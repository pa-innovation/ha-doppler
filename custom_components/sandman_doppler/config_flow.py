"""Adds config flow for Doppler."""
from __future__ import annotations

from doppyler.client import DopplerClient
from doppyler.exceptions import DopplerException
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .const import DOMAIN


class DopplerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Doppler clocks."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] = None) -> FlowResult:
        """Handle a flow initialized by the user."""
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
            step_id="user",
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

    async def _credentials_valid(self, email: str, password: str) -> bool:
        """Return true if credentials are valid."""
        session = async_get_clientsession(self.hass)
        client = DopplerClient(email, password, client_session=session)
        try:
            await client.get_token()
        except DopplerException:
            return False
        return True
