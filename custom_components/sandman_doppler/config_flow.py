"""Adds config flow for Blueprint."""
from doppyler.client import DopplerClient
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers import config_validation as cv
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession
import voluptuous as vol

from .const import DOMAIN


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input: dict[str, str] = None) -> FlowResult:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL])
            self._abort_if_unique_id_configured()

            valid = await self._test_credentials(
                user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
            if valid:
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL], data=user_input
                )
            else:
                self._errors["base"] = "auth"

            return self._show_config_form()

        return self._show_config_form()

    @callback
    def _show_config_form(self) -> FlowResult:
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_LATITUDE,
                                 default=self.hass.config.latitude): cv.latitude,
                    vol.Required(CONF_LONGITUDE,
                                 default=self.hass.config.longitude) : cv.longitude
                }
            ),
            errors=self._errors,
        )

    async def _test_credentials(self, email: str, password: str) -> bool:
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = DopplerClient(email, password, client_session=session)
            await client.get_devices()
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False
