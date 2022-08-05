"""The Sandman Doppler integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import voluptuous as vol
from typing import Any
from aiohttp.client import ClientTimeout, DEFAULT_TIMEOUT

from doppyler.client import DopplerClient
from doppyler.model.doppler import Doppler
from doppyler.model.alarm import Alarm
from doppyler.model.alarm import RepeatDayOfWeek
from doppyler.model.alarm import AlarmStatus
from doppyler.model.alarm import AlarmSource
from doppyler.model.alarm import AlarmDict
from doppyler.model.color import Color
from doppyler.model.color import ColorDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
#from homeassistant.helpers.device_registry import async_get
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr


from .const import (
    ATTR_ALARM_SOUNDS,
    ATTR_ALARMS,
    ATTR_AUTO_BRIGHTNESS_ENABLED,
    ATTR_DAY_BUTTON_COLOR,
    ATTR_NIGHT_BUTTON_COLOR,
    ATTR_DAY_DISPLAY_BRIGHTNESS,
    ATTR_NIGHT_DISPLAY_BRIGHTNESS,
    ATTR_DAY_BUTTON_BRIGHTNESS,
    ATTR_NIGHT_BUTTON_BRIGHTNESS,
    ATTR_DAY_DISPLAY_COLOR,
    ATTR_NIGHT_DISPLAY_COLOR,
    ATTR_DOTW_STATUS,
    ATTR_TIME_MODE,
    ATTR_VOLUME_LEVEL,
    ATTR_WEATHER,
    ATTR_WIFI,
    ATTR_COLON_BLINK,
    ATTR_USE_COLON,
    ATTR_USE_LEADING_ZERO,
    ATTR_DISPLAY_SECONDS,
    ATTR_ALEXA_USE_ASCENDING_ALARMS,
    ATTR_ALEXA_TAPTALK_TONE,
    ATTR_ALEXA_WAKEWORD_TONE,
    ATTR_SOUND_PRESET,
    ATTR_SOUND_PRESET_MODE,
    ATTR_WEATHER_ON,
    ATTR_WEATHER_MODE,
    ATTR_LIGHTSENSOR_VALUE,
    ATTR_DAYNIGHTMODE_VALUE,
    ATTR_TIMEOFFSET,
    ATTR_TIMEZONE,
    WEATHER_OPTIONS,
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE,
)

SCAN_INTERVAL = timedelta(seconds=300)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    email = entry.data.get(CONF_EMAIL)
    password = entry.data.get(CONF_PASSWORD)

    session = async_create_clientsession(hass, timeout=ClientTimeout(DEFAULT_TIMEOUT))
    client = DopplerClient(email, password, client_session=session)

    coordinator = DopplerDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            hass.async_add_job(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    entry.add_update_listener(async_reload_entry)
    #entry.async_on_unload(entry.add_update_listener(update_listener))
    #entry.add_update_listener(update_listener)

    mydevices= await client.get_devices()
    for device in mydevices.values():
        await client.set_sync_button_display_color(device, False)
        await client.set_sync_day_night_color(device, False)
        await client.set_sync_button_display_brightness(device, False)
        await client.set_weather_location(device, f"{entry.data.get(CONF_LATITUDE):.6f},{entry.data.get(CONF_LONGITUDE):.6f}")

    async def handle_set_alarm_service(call):
        deviceregistry=dr.async_get(hass)
        deviceentry=deviceregistry.async_get(call.data['doppler_device_id'])
        _LOGGER.warning(f"Calling setalarm {call.data['alarm_time']} {deviceentry.identifiers}")
        _LOGGER.warning(f"printing config entries{deviceentry.config_entries}")
        mydevice=""
        for device in mydevices.values():
            if ('sandman_doppler',device.id) in deviceentry.identifiers:
                _LOGGER.warning(f"managed to locate the device id")
                mydevice=device
                break
        if mydevice != "":
            if 'repeat' in call.data:
                r=call.data['repeat']
            else:
                r=""
            alarmdict=AlarmDict(id= int(call.data['alarm_id']),
                                name=call.data['alarm_name'],
                                time_hr=int(call.data['alarm_time'].split(':')[0]),
                                time_min=int(call.data['alarm_time'].split(':')[1]),
                                repeat=r,
                                color=ColorDict(red=int(call.data['color'][0]),
                                                green=int(call.data['color'][1]),
                                                blue= int(call.data['color'][2])),
                                volume=int(call.data['volume']),
                                status=AlarmStatus.SET,
                                src=AlarmSource.APP,
                                sound=call.data['sound']
                                )
                                
            alarm=Alarm(mydevice, alarmdict);
            result= await client.append_new_alarm(mydevice,alarm)
            _LOGGER.warning(f"alarm result was {result}")

    async def handle_delete_alarm_service(call):
        deviceregistry=dr.async_get(hass)
        deviceentry=deviceregistry.async_get(call.data['doppler_device_id'])
        mydevice=""
        for device in mydevices.values():
            if ('sandman_doppler',device.id) in deviceentry.identifiers:
                _LOGGER.warning(f"managed to locate the device id")
                mydevice=device
                break
        if mydevice != "":
            await client.delete_alarm(mydevice,int(call.data['alarm_id']))
        
    hass.services.async_register(DOMAIN,"setalarmservice",handle_set_alarm_service)
    hass.services.async_register(DOMAIN,"deletealarmservice",handle_delete_alarm_service)


    

        
    return True

async def update_listener(hass,entry):
    _LOGGER.warning("should be logging conf_latitude")
    _LOGGER.warning(entry.options.get(CONF_LATITUDE))


class DopplerDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: DopplerClient
    ) -> None:
        """Initialize."""
        self.api = client
        self.platforms = []
        self._dev_reg = None
        self._entry = entry

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        
        
    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        if not self._dev_reg:
            self._dev_reg = dr.async_get(self.hass)

        data: dict[str, Any] = {}
        devices: dict[str, Doppler] = {}
        if self.api.devices:
            devices = self.api.devices
        await self.api.get_devices()
        if devices != self.api.devices:
            # TODO: Signal add entities for the new device
            pass

        try:
            for device in self.api.devices.values():
                self._dev_reg.async_get_or_create(
                    config_entry_id=self._entry.entry_id,
                    identifiers={(DOMAIN, device.id)},
                    manufacturer=device.device_info.manufacturer,
                    model=device.device_info.model_number,
                    sw_version=device.device_info.software_version,
                    name=device.name,
                )
                device_data = data.setdefault(device.name, {})
                await asyncio.sleep(0.5)
                device_data[ATTR_DAY_BUTTON_COLOR] = await self.api.get_day_button_color(device)
                await asyncio.sleep(0.5)
                device_data[ATTR_NIGHT_BUTTON_COLOR] = await self.api.get_night_button_color(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_DAY_DISPLAY_COLOR] = await self.api.get_day_display_color(
                    device
                )
                await asyncio.sleep(0.5)
                device_data[ATTR_NIGHT_DISPLAY_COLOR] = await self.api.get_night_display_color(
                    device
                )
                await asyncio.sleep(0.5)
                device_data[
                    ATTR_DAY_DISPLAY_BRIGHTNESS
                ] = await self.api.get_day_display_brightness(device)
                await asyncio.sleep(0.5)
                device_data[
                    ATTR_NIGHT_DISPLAY_BRIGHTNESS
                ] = await self.api.get_night_display_brightness(device)
                await asyncio.sleep(0.5)
                device_data[
                    ATTR_DAY_BUTTON_BRIGHTNESS
                ] = await self.api.get_day_button_brightness(device)
                await asyncio.sleep(0.5)

                device_data[
                    ATTR_NIGHT_BUTTON_BRIGHTNESS
                ] = await self.api.get_night_button_brightness(device)
                await asyncio.sleep(0.5)

                
                device_data[
                    ATTR_AUTO_BRIGHTNESS_ENABLED
                ] = await self.api.is_automatic_brightness_enabled(device)
                await asyncio.sleep(0.5)
                # device_data[
                #     ATTR_DOTW_STATUS
                # ] = await self.api.get_day_of_the_week_status(device)
                # await asyncio.sleep(0.5)
                device_data[ATTR_VOLUME_LEVEL] = await self.api.get_volume_level(device)
                await asyncio.sleep(0.5)
                device_data[ATTR_TIME_MODE] = await self.api.get_time_mode(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_ALARMS] = await self.api.get_all_alarms(device)
                await asyncio.sleep(0.5)

                # device_data[ATTR_WEATHER] = await self.api.get_weather_configuration(
                #     device
                # )
                # await asyncio.sleep(0.5)
                device_data[ATTR_WIFI] = await self.api.get_wifi_status(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_COLON_BLINK]= await self.api.get_colon_blink_mode(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_USE_COLON] = await self.api.get_use_colon_mode(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_USE_LEADING_ZERO] = await self.api.get_use_leading_zero_mode(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_DISPLAY_SECONDS] = await self.api.get_display_seconds_mode(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_ALEXA_USE_ASCENDING_ALARMS] = await self.api.get_alexa_ascending_alarms_mode(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_ALEXA_TAPTALK_TONE] = await self.api.get_alexa_taptalk_tone_mode(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_ALEXA_WAKEWORD_TONE] = await self.api.get_alexa_wakeword_tone_mode(device)
                await asyncio.sleep(0.5)

                preset=await self.api.get_sound_preset(device)
                if preset=="PRESET1":
                    device_data[ATTR_SOUND_PRESET]="Preset 1 Balanced"
                elif preset=="PRESET2":
                    device_data[ATTR_SOUND_PRESET]="Preset 2 Bass Boost"
                elif preset=="PRESET3":
                    device_data[ATTR_SOUND_PRESET]="Preset 3 Treble Boost"
                elif preset=="PRESET4":
                    device_data[ATTR_SOUND_PRESET]="Preset 4 Mids Boost"
                elif preset=="PRESET5":
                    device_data[ATTR_SOUND_PRESET]="Preset 5 Untuned"

                await asyncio.sleep(0.5)

                device_data[ATTR_SOUND_PRESET_MODE] = await self.api.get_sound_preset_mode(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_WEATHER_ON] = await self.api.get_weather_status(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_WEATHER_MODE] = WEATHER_OPTIONS[await self.api.get_weather_mode(device)]
                await asyncio.sleep(0.5)

                device_data[ATTR_LIGHTSENSOR_VALUE] = await self.api.get_lightsensor_value(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_DAYNIGHTMODE_VALUE] = await self.api.get_daynightmode_value(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_TIMEOFFSET] = await self.api.get_offset(device)
                await asyncio.sleep(0.5)

                device_data[ATTR_TIMEZONE] = await self.api.get_timezone(device)
                await asyncio.sleep(0.5)

                
        except Exception as exception:
            raise UpdateFailed() from exception

        return data


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
