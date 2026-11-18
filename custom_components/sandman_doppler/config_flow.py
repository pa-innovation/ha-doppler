"""Adds config flow for Doppler."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_EMAIL,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_DSN, CONF_LOCAL_KEY, DEFAULT_LOCAL_PORT, DOMAIN
from .doppyler.client import DopplerClient
from .doppyler.exceptions import (
    DopplerException,
    ExpiredNonce,
    SerialMismatch,
    UnauthorizedException,
)

_LOGGER = logging.getLogger(__name__)

_KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

LOCAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Doppler"): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_LOCAL_PORT): cv.port,
        vol.Required(CONF_DSN): cv.string,
        vol.Required(CONF_LOCAL_KEY): _KEY_SELECTOR,
    }
)

RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_LOCAL_PORT): cv.port,
        # Left empty, the stored key is kept.
        vol.Optional(CONF_LOCAL_KEY): _KEY_SELECTOR,
    }
)


class DopplerFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Doppler clocks."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user choose a Sandman account or a local-only clock."""
        return self.async_show_menu(step_id="user", menu_options=["cloud", "local"])

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up all clocks of a Sandman account (cloud login, local control)."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()

            if await self._credentials_valid(
                user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            ):
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )
            else:
                errors["base"] = "auth"

        user_input = user_input or {}

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL, default=user_input.get(CONF_EMAIL)
                    ): cv.string,
                    vol.Required(
                        CONF_PASSWORD, default=user_input.get(CONF_PASSWORD)
                    ): cv.string,
                }
            ),
            errors=errors,
        )

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up one clock on the local network, without Sandman's cloud."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_NAME: user_input[CONF_NAME].strip(),
                CONF_HOST: user_input[CONF_HOST].strip(),
                CONF_PORT: user_input[CONF_PORT],
                CONF_DSN: user_input[CONF_DSN].strip(),
                CONF_LOCAL_KEY: user_input[CONF_LOCAL_KEY].strip(),
            }
            await self.async_set_unique_id(data[CONF_DSN].lower())
            self._abort_if_unique_id_configured()
            if self._dsn_in_other_entry(data[CONF_DSN]):
                return self.async_abort(reason="already_configured_device")
            error, reported_dsn = await self._check_local_clock(data)
            if error is None:
                data[CONF_DSN] = reported_dsn
                return self.async_create_entry(title=data[CONF_NAME], data=data)
            errors["base"] = error

        return self.async_show_form(
            step_id="local",
            data_schema=self.add_suggested_values_to_schema(
                LOCAL_SCHEMA,
                {k: v for k, v in (user_input or {}).items() if k != CONF_LOCAL_KEY},
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change a local clock's address or key (for example after a DHCP change)."""
        entry = self._get_reconfigure_entry()
        if CONF_HOST not in entry.data:
            return self.async_abort(reason="reconfigure_cloud_unsupported")
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                **entry.data,
                CONF_HOST: user_input[CONF_HOST].strip(),
                CONF_PORT: user_input[CONF_PORT],
            }
            if new_key := (user_input.get(CONF_LOCAL_KEY) or "").strip():
                data[CONF_LOCAL_KEY] = new_key
            error, _ = await self._check_local_clock(data)
            if error is None:
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                RECONFIGURE_SCHEMA,
                {
                    CONF_HOST: entry.data[CONF_HOST],
                    CONF_PORT: entry.data[CONF_PORT],
                },
            ),
            errors=errors,
        )

    async def _credentials_valid(self, email: str, password: str) -> bool:
        """Return true if credentials are valid."""
        session = async_get_clientsession(self.hass)
        client = DopplerClient(email, password, client_session=session)
        try:
            await client.get_token()
        except DopplerException:
            return False
        return True

    def _dsn_in_other_entry(self, dsn: str) -> bool:
        """Return true if a clock with this DSN already belongs to another entry."""
        dev_reg = dr.async_get(self.hass)
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
                for ident in device.identifiers:
                    # Other integrations may use identifiers that aren't 2-tuples.
                    if ident[0] == DOMAIN and str(ident[1]).lower() == dsn.lower():
                        return True
        return False

    async def _check_local_clock(
        self, data: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        """Try the clock with the given key.

        Returns (error key, None) on failure or (None, serial as the clock reports it).
        """
        if not data[CONF_LOCAL_KEY].isascii():
            return "invalid_local_key", None
        session = async_get_clientsession(self.hass)
        client = DopplerClient(None, None, client_session=session)
        try:
            doppler = await client.add_local_device(
                data[CONF_DSN],
                data.get(CONF_NAME, "Doppler"),
                data[CONF_HOST],
                data[CONF_PORT],
                data[CONF_LOCAL_KEY],
                notify=False,
            )
        except (ExpiredNonce, UnauthorizedException):
            return "invalid_local_key", None
        except SerialMismatch:
            return "wrong_device", None
        except DopplerException as err:
            _LOGGER.debug("Local Doppler check failed: %s", type(err).__name__)
            return "cannot_connect", None
        return None, doppler.dsn
