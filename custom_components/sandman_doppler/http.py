"""HTTP views for Sandman Doppler."""

from __future__ import annotations

from http import HTTPStatus
import logging

from aiohttp.web import Request, Response

from homeassistant.components.http.view import HomeAssistantView
from homeassistant.const import ATTR_DEVICE_ID, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import ATTR_DOPPLER_NAME, ATTR_DSN, DOMAIN, EVENT_BUTTON_PRESSED

_LOGGER = logging.getLogger(__name__)


class DopplerWebhookView(HomeAssistantView):
    """Provide a page for the device to call."""

    requires_auth = False
    cors_allowed = True
    url = r"/api/sandman_doppler/smart_button/{device_id}"
    name = "api:sandman_doppler:smart_button"

    def __init__(self) -> None:
        """Initialize view."""
        super().__init__()
        self._dev_reg: dr.DeviceRegistry | None = None

    async def post(self, request: Request, device_id: str) -> Response:
        """Respond to requests from the device."""
        hass: HomeAssistant = request.app["hass"]
        if not self._dev_reg:
            self._dev_reg = dr.async_get(hass)

        device = self._dev_reg.async_get(device_id)
        if not device:
            _LOGGER.error("Device not found: %s", device_id)
            return Response(status=HTTPStatus.OK)
        if not (
            identifier := next(
                (
                    identifier
                    for identifier in device.identifiers
                    if identifier[0] == DOMAIN
                ),
                None,
            )
        ):
            _LOGGER.error("Device not a Sandman Doppler device: %s", device_id)
            return Response(status=HTTPStatus.OK)

        data = await request.json()
        if not (dsn := data.get(ATTR_DSN)):
            _LOGGER.error("Invalid request: %s", data)
            return Response(status=HTTPStatus.OK)
        if identifier[1] != dsn:
            _LOGGER.error(
                "DSN sent (%s) does not match device entry: %s (%s)",
                dsn,
                device_id,
                identifier[1],
            )
            return Response(status=HTTPStatus.OK)

        hass.bus.async_fire(
            EVENT_BUTTON_PRESSED,
            {
                **data,
                ATTR_DOPPLER_NAME: device.name,
                ATTR_NAME: device.name_by_user or device.name,
                ATTR_DEVICE_ID: device_id,
            },
        )
        return Response(status=HTTPStatus.OK)
