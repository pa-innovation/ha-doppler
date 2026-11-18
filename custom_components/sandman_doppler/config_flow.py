"""Adds config flow for Doppler."""

from __future__ import annotations

import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_EMAIL,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_DSN, CONF_LOCAL_KEY, DEFAULT_LOCAL_PORT, DOMAIN
from .doppyler.client import DopplerClient
from .doppyler.exceptions import (
    DopplerException,
    ExpiredNonce,
    UnauthorizedException,
)

_LOGGER = logging.getLogger(__name__)


class DopplerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Doppler clocks."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] = None) -> FlowResult:
        """Let the user choose a Sandman account or a local-only clock."""
        return self.async_show_menu(step_id="user", menu_options=["cloud", "local"])

    async def async_step_cloud(self, user_input: dict[str, str] = None) -> FlowResult:
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

    async def async_step_local(self, user_input: dict[str, str] = None) -> FlowResult:
        """Set up one clock on the local network, without Sandman's cloud."""
        errors = {}

        if user_input is not None:
            dsn = user_input[CONF_DSN].strip()
            await self.async_set_unique_id(dsn)
            self._abort_if_unique_id_configured()
            error = await self._local_clock_error(
                dsn,
                user_input[CONF_NAME],
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_LOCAL_KEY],
            )
            if error is None:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data={**user_input, CONF_DSN: dsn}
                )
            errors["base"] = error

        user_input = user_input or {}

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=user_input.get(CONF_NAME, "Doppler")
                    ): cv.string,
                    vol.Required(CONF_HOST, default=user_input.get(CONF_HOST)): cv.string,
                    vol.Required(
                        CONF_PORT, default=user_input.get(CONF_PORT, DEFAULT_LOCAL_PORT)
                    ): cv.port,
                    vol.Required(CONF_DSN, default=user_input.get(CONF_DSN)): cv.string,
                    vol.Required(CONF_LOCAL_KEY): cv.string,
                }
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

    async def _local_clock_error(
        self, dsn: str, name: str, host: str, port: int, local_key: str
    ) -> str | None:
        """Try the clock with the given key; return an error key, or None if it works."""
        session = async_get_clientsession(self.hass)
        client = DopplerClient(None, None, client_session=session)
        try:
            await client.add_local_device(dsn, name, host, port, local_key)
        except (ExpiredNonce, UnauthorizedException):
            return "invalid_local_key"
        except DopplerException as err:
            _LOGGER.debug("Local Doppler check failed: %s", type(err).__name__)
            return "cannot_connect"
        except (aiohttp.ClientError, OSError) as err:
            _LOGGER.debug("Local Doppler unreachable: %s", type(err).__name__)
            return "cannot_connect"
        return None
