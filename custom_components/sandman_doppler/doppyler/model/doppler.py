"""Model for Doppler clock."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any, Callable, Literal, TypedDict
from zoneinfo import ZoneInfo

from ..const import (
    ATTR_ALARM_SOUNDS,
    ATTR_ALARMS,
    ATTR_ALEXA_TAP_TO_TALK_TONE_ENABLED,
    ATTR_ALEXA_USE_ASCENDING_ALARMS,
    ATTR_ALEXA_WAKE_WORD_TONE_ENABLED,
    ATTR_COLON_BLINK,
    ATTR_CONNECTED_TO_ALEXA,
    ATTR_DAY_BUTTON_BRIGHTNESS,
    ATTR_DAY_BUTTON_COLOR,
    ATTR_DAY_DISPLAY_BRIGHTNESS,
    ATTR_DAY_DISPLAY_COLOR,
    ATTR_DAY_TO_NIGHT_TRANSITION_VALUE,
    ATTR_DISPLAY_SECONDS,
    ATTR_IS_IN_DAY_MODE,
    ATTR_LIGHT_SENSOR_VALUE,
    ATTR_NIGHT_BUTTON_BRIGHTNESS,
    ATTR_NIGHT_BUTTON_COLOR,
    ATTR_NIGHT_DISPLAY_BRIGHTNESS,
    ATTR_NIGHT_DISPLAY_COLOR,
    ATTR_NIGHT_TO_DAY_TRANSITION_VALUE,
    ATTR_SMART_BUTTON_COLOR,
    ATTR_SOUND_PRESET,
    ATTR_SOUND_PRESET_MODE,
    ATTR_SPEED,
    ATTR_SYNC_BUTTON_AND_DISPLAY_BRIGHTNESS,
    ATTR_SYNC_BUTTON_AND_DISPLAY_COLOR,
    ATTR_SYNC_DAY_AND_NIGHT_COLOR,
    ATTR_TIME_MODE,
    ATTR_TIME_OFFSET,
    ATTR_TIMEZONE,
    ATTR_USE_COLON,
    ATTR_USE_FADE_TIME,
    ATTR_USE_LEADING_ZERO,
    ATTR_VOLUME_LEVEL,
    ATTR_WEATHER,
    ATTR_WEATHER_WAKE_UP_TIME,
    ATTR_WIFI,
)
from ..exceptions import ExpiredNonce, InvalidAlarmSound, UnauthorizedException
from .alarm import Alarm
from .color import Color
from .light_bar import LightBarDisplayEffect
from .main_display_text import MainDisplayText
from .mini_display_number import MiniDisplayNumber
from .rainbow import RainbowConfiguration, RainbowMode
from .smart_button import SmartButtonConfiguration
from .sound import SoundPreset
from .weather import WeatherConfiguration, WeatherMode
from .wifi import WifiStatus

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..client import DopplerClient

_ZONEINFO_CACHE: dict[str, ZoneInfo] = {}


async def _async_get_zoneinfo(timezone_str: str) -> ZoneInfo:
    """Return the ZoneInfo for a timezone string from the clock.

    ZoneInfo reads the zone's file from disk the first time a key is used, so the
    first lookup of each key runs in the executor to keep blocking I/O out of the
    event loop. Later lookups are served from a cache without a thread hop.
    """
    # Hack to get around timezone string bug
    key = "/".join(part for part in timezone_str.split("/") if part)
    if (zone := _ZONEINFO_CACHE.get(key)) is None:
        zone = await asyncio.get_running_loop().run_in_executor(None, ZoneInfo, key)
        _ZONEINFO_CACHE[key] = zone
    return zone


class DeviceInfoDict(TypedDict):
    """Device info dict as returned from API."""

    mfgrName: str
    modelNum: str
    serialNum: str
    firmware: str
    hardware: str
    software: str


class LocalInfoDict(TypedDict):
    """Local info dict as gathered from localkey API call."""

    localkey: str
    ipAddie: str
    port: int


class DopplerDeviceInfo:
    """Doppler device info class."""

    def __init__(self, device_info: DeviceInfoDict) -> None:
        """Initialize device info."""
        self.dsn = device_info["serialNum"]
        self.manufacturer = device_info["mfgrName"]
        self.model_number = device_info["modelNum"]
        self.firmware_version = device_info["firmware"]
        self.hardware_version = device_info["hardware"]
        self.software_version = device_info["software"]

    def __repr__(self) -> str:
        """Return representation."""
        return (
            f"DopplerDeviceInfo(dsn={self.dsn}, manufacturer={self.manufacturer}, "
            f"model_number={self.model_number}, firmware_version="
            f"{self.firmware_version}, hardware_version={self.hardware_version}, "
            f"software_version={self.software_version})"
        )

    update = __init__


class DopplerLocalInfo:
    """Doppler Local Control Info class."""

    def __init__(self, local_info: LocalInfoDict) -> None:
        """Initialize local info."""
        self.local_key = local_info["localkey"]
        self.ip_address = local_info["ipAddie"]
        self.port = local_info["port"]

    def __repr__(self) -> str:
        """Return string representation of DopplerLocalInfo."""
        return f"DopplerLocalInfo(ip={self.ip_address}, port={self.port})"

    update = __init__


class Doppler:
    """Doppler clock class."""

    def __init__(
        self,
        client: "DopplerClient",
        name: str,
        device_info: DeviceInfoDict,
        local_info: LocalInfoDict,
        local_control: bool,
        local_api_semaphore_limit: int,
    ) -> None:
        """Initialize Doppler."""
        self._local_api_semaphore = asyncio.Semaphore(local_api_semaphore_limit)
        self._nonce_event = asyncio.Event()
        self._nonce_event.set()

        self.client = client
        self.name = name
        self.device_info = DopplerDeviceInfo(device_info)
        self.local_info = DopplerLocalInfo(local_info)
        self.local_control = local_control
        self.alarm_sounds: list[str] = []
        self.alarms: dict[int, Alarm] = {}

        # Set local path
        self.local_path = f"https://{self.local_info.ip_address}:{self.local_info.port}"

        # Auth data
        self._nonce: str | None = None
        self._final_key: str | None = None
        self._nonce_expires: datetime | None = None

        self._removed_alarm_listeners: list[Callable[[Alarm], None]] = []
        self._added_alarm_listeners: list[Callable[[Alarm], None]] = []
        self._loop = asyncio.get_running_loop()

    @property
    def dsn(self) -> str:
        """Return device serial number."""
        return self.device_info.dsn

    def __repr__(self) -> str:
        """Return string representation of a Doppler device."""
        return f"Doppler(name={self.name}, dsn={self.dsn})"

    async def _call_local_api(
        self, endpoint: str, method: str = "GET", data: dict = None
    ) -> dict:
        """Make an API call for a doppler with local control."""
        # Bounds the number of concurrent requests to the doppler
        async with self._local_api_semaphore:
            # Block other calls while getting a new nonce
            await self._nonce_event.wait()
            if self._nonce_event.is_set() and (
                not self._nonce or datetime.now() > self._nonce_expires
            ):
                await self._get_nonce_and_final_key()

            # The clock's local API uses a certificate that can't be verified, so
            # local requests skip TLS verification (cloud requests don't).
            try:
                return await self.client.request(
                    f"{self.local_path}/{self.dsn}/{endpoint}",
                    method,
                    data,
                    {"Authorization": f"Bearer {self._final_key}"},
                    verify_ssl=False,
                )
            except (ExpiredNonce, UnauthorizedException):
                if self._nonce_event.is_set():
                    await self._get_nonce_and_final_key()
                await self._nonce_event.wait()
                return await self.client.request(
                    f"{self.local_path}/{self.dsn}/{endpoint}",
                    method,
                    data,
                    {"Authorization": f"Bearer {self._final_key}"},
                    verify_ssl=False,
                )

    async def _get_nonce_and_final_key(self):
        """Get the nonce and calculate the final key."""
        self._nonce_event.clear()
        nonce_json = await self.client.request(
            f"{self.local_path}/{self.dsn}/nonce", verify_ssl=False
        )
        self._nonce = nonce = nonce_json["nonce"]
        self._nonce_expires = datetime.now() + timedelta(days=1)
        m = hashlib.sha256()
        m.update(nonce.encode("ascii"))
        m.update(self.local_info.local_key.encode("ascii"))
        self._final_key = f"{nonce}|{base64.b64encode(m.digest()).decode('ascii')}"
        self._nonce_event.set()

    async def _call_api(
        self, endpoint: str, method: str = "GET", data: dict = None
    ) -> dict:
        """Make an API call for a doppler."""
        if self.local_control:
            return await self._call_local_api(endpoint, method=method, data=data)
        return await self.client.call_cloud_api(
            self.dsn, endpoint, method=method, data=data
        )

    def update(
        self, name: str, device_info: DeviceInfoDict, local_info: LocalInfoDict
    ) -> None:
        """Update name, device info, and local info."""
        self.name = name
        self.device_info.update(device_info)
        self.local_info.update(local_info)

    def _call_alarm_listeners(self, alarm: Alarm, listeners: list) -> None:
        """Call all listeners."""
        for listener in listeners.copy():
            if asyncio.iscoroutinefunction(listener):
                self._loop.create_task(listener(alarm))
            else:
                listener(alarm)

    async def get_wifi_status(self) -> WifiStatus:
        """Get the status of the WiFi on the device."""
        wifi_status = await self._call_api("hardware/wifi-status")
        return WifiStatus.from_dict(wifi_status)

    async def get_utc_time(self) -> time:
        """Get the UTC time from the clock."""
        time_ = await self._call_api("doptime/utc-time")
        return time(hour=time_["hour"], minute=time_["min"])

    async def get_time_mode(self) -> Literal[12, 24]:
        """Get time mode."""
        time_mode = await self._call_api("software/time-mode")
        return time_mode["timeMode"]

    async def set_time_mode(self, time_mode: Literal[12, 24]) -> Literal[12, 24]:
        """Set time mode."""
        data = {"timeMode": time_mode}
        new_time_mode = await self._call_api("software/time-mode", "PUT", data)
        return new_time_mode["timeMode"]

    async def get_timezone(self) -> ZoneInfo:
        """Get the timezone."""
        timezone = await self._call_api("doptime/timezone")
        return await _async_get_zoneinfo(timezone["timezone"])

    async def set_timezone(self, timezone: ZoneInfo) -> ZoneInfo:
        """Set the timezone."""
        data = {"timezone": timezone.key}
        timezone = await self._call_api("doptime/timezone", "PUT", data)
        return await _async_get_zoneinfo(timezone["timezone"])

    async def get_offset(self) -> timedelta:
        """Get the offset from UTC in minutes."""
        offset = await self._call_api("doptime/offset")
        return timedelta(minutes=offset["offset"])

    async def set_offset(self, offset: timedelta) -> timedelta:
        """Set the offset from UTC in minutes."""
        data = {"offset": int(offset.total_seconds() // 60)}
        offset = await self._call_api("doptime/offset", "PUT", data)
        return timedelta(minutes=offset["offset"])

    async def get_use_colon_mode(self) -> bool:
        """Get whether colon should be on."""
        use_colon_mode = await self._call_api("software/use-colon")
        return use_colon_mode["on"]

    async def set_use_colon_mode(self, on: bool) -> bool:
        """Set whether colon should be on."""
        data = {"on": on}
        use_colon_mode = await self._call_api("software/use-colon", "PUT", data)
        return use_colon_mode["on"]

    async def get_colon_blink_mode(self) -> bool:
        """Get whether colon blinks."""
        colon_blink_mode = await self._call_api("software/colon-blink")
        return colon_blink_mode["blink"]

    async def set_colon_blink_mode(self, blink: bool) -> bool:
        """Set whether colon blinks."""
        data = {"blink": blink}
        colon_blink_mode = await self._call_api("software/colon-blink", "PUT", data)
        return colon_blink_mode["blink"]

    async def get_use_leading_zero_mode(self) -> bool:
        """Get whether leading zero should be on."""
        use_leading_zero_mode = await self._call_api("software/use-leading-zero")
        return use_leading_zero_mode["on"]

    async def set_use_leading_zero_mode(self, on: bool) -> bool:
        """Set whether leading zero should be on."""
        data = {"on": on}
        use_leading_zero_mode = await self._call_api(
            "software/use-leading-zero", "PUT", data
        )
        return use_leading_zero_mode["on"]

    async def get_use_fade_time(self) -> bool:
        """Get whether fade time should be on."""
        use_fade_time = await self._call_api("software/use-leading-zero")
        return use_fade_time["on"]

    async def set_use_fade_time(self, on: bool) -> bool:
        """Set whether fade time should be on."""
        data = {"on": on}
        use_fade_time = await self._call_api("software/use-fade-time", "PUT", data)
        return use_fade_time["on"]

    async def get_display_seconds_mode(self) -> bool:
        """Get whether to display seconds on the small display."""
        use_display_seconds = await self._call_api("software/display-seconds")
        return use_display_seconds["on"]

    async def set_display_seconds_mode(self, on: bool) -> bool:
        """Set whether to display seconds on the small display."""
        data = {"on": on}
        use_display_seconds = await self._call_api(
            "software/display-seconds", "PUT", data
        )
        return use_display_seconds["on"]

    async def get_volume_level(self) -> int:
        """Get current volume level (0-100)."""
        volume = await self._call_api("hardware/volume")
        return volume["volume"]

    async def set_volume_level(self, volume: int) -> int:
        """Set volume level (0-100)."""
        data = {"volume": volume}
        volume = await self._call_api("hardware/volume", "PUT", data)
        return volume["volume"]

    async def get_sound_preset(self) -> SoundPreset:
        """Get the clocks audio preset."""
        preset = await self._call_api("hardware/sound-preset")
        return SoundPreset(preset["preset"])

    async def set_sound_preset(self, val: SoundPreset) -> SoundPreset:
        """Set the clocks audio preset."""
        data = {"preset": val.value}
        preset = await self._call_api("hardware/sound-preset", "PUT", data)
        return SoundPreset(preset["preset"])

    async def get_sound_preset_mode(self) -> bool:
        """Get whether doppler should use volume dependent eq."""
        mode = await self._call_api("hardware/sound-preset-mode")
        return bool(mode["presetmode"])

    async def set_sound_preset_mode(self, auto_tune: bool) -> bool:
        """Set whether doppler should do volume dependent eq."""
        data = {"presetmode": int(auto_tune)}
        mode = await self._call_api("hardware/sound-preset-mode", "PUT", data)
        return bool(mode["presetmode"])

    def on_alarm_removed(
        self, callback: Callable[[Alarm], None]
    ) -> Callable[[None], None]:
        """Register a callback for when an alarm is removed."""
        self._removed_alarm_listeners.append(callback)

        def unsubscribe() -> None:
            """Unsubscribe listeners."""
            if callback in self._removed_alarm_listeners:
                self._removed_alarm_listeners.remove(callback)

        return unsubscribe

    def on_alarm_added(
        self, callback: Callable[[Alarm], None]
    ) -> Callable[[None], None]:
        """Register a callback for when an alarm is added."""
        self._added_alarm_listeners.append(callback)

        def unsubscribe() -> None:
            """Unsubscribe listeners."""
            if callback in self._added_alarm_listeners:
                self._added_alarm_listeners.remove(callback)

        return unsubscribe

    async def get_all_alarms(self) -> dict[int, Alarm]:
        """Get all alarms."""
        new_alarms = {
            alarm.id: alarm
            for alarm in sorted(
                [
                    Alarm.from_dict(alarm)
                    for alarm in (await self._call_api("alarms"))["alarms"]
                ],
                key=lambda x: x.id,
            )
        }

        new_alarm_ids = set(new_alarms)
        existing_alarm_ids = set(self.alarms)

        # Update existing alarms
        for alarm_id in new_alarm_ids & existing_alarm_ids:
            self.alarms[alarm_id].update(new_alarms[alarm_id])

        # Add new alarms and call on added listeners
        for alarm_id in new_alarm_ids - existing_alarm_ids:
            self.alarms[alarm_id] = new_alarms[alarm_id]
            self._call_alarm_listeners(
                self.alarms[alarm_id], self._added_alarm_listeners
            )

        # Remove deleted alarms and call on removed listeners
        for alarm_id in existing_alarm_ids - new_alarm_ids:
            self._call_alarm_listeners(
                self.alarms.pop(alarm_id), self._removed_alarm_listeners
            )

        return self.alarms

    async def add_alarm(self, alarm: Alarm) -> list[Alarm]:
        """Add new alarm."""
        if self.alarm_sounds and alarm.sound not in self.alarm_sounds:
            raise InvalidAlarmSound(self, alarm.sound)
        data = alarm.to_dict()
        alarms = await self._call_api("alarms", "POST", data)
        return sorted(
            [Alarm.from_dict(alarm) for alarm in alarms["alarms"]], key=lambda x: x.id
        )

    async def update_alarm(self, id_: int, alarm: Alarm) -> list[Alarm]:
        """Update existing alarms."""
        data = alarm.to_dict()
        alarms = await self._call_api(f"alarms/{id_}", "PUT", data)
        return sorted(
            [Alarm.from_dict(alarm) for alarm in alarms["alarms"]], key=lambda x: x.id
        )

    async def upsert_alarm(self, id_: int, alarm: Alarm) -> Alarm:
        """Set an alarm on a particular alarm id."""
        data = alarm.to_dict()
        alarm = await self._call_api(f"alarms/{id_}", "POST", data)
        return Alarm.from_dict(alarm)

    async def delete_alarm(self, id_: int) -> list[Alarm]:
        """Delete an alarm."""
        alarms = await self._call_api(f"alarms/{id_}", "DELETE")
        return sorted(
            [Alarm.from_dict(alarm) for alarm in alarms["alarms"]], key=lambda x: x.id
        )

    async def get_alarm_sounds(self) -> list[str]:
        """Get available alarm sounds."""
        sounds = sorted((await self._call_api("alarms/sounds"))["sounds"])
        if sounds != self.alarm_sounds:
            self.alarm_sounds.clear()
            self.alarm_sounds.extend(sounds)
        return self.alarm_sounds

    async def _get_alarm_sound_volume(self, volume: int | None) -> int:
        """Return the "vol" to send with an alarms/sounds/play request.

        The clock requires "vol" as an integer 0-100: without it the request fails
        with 404 "alarm not found", and a float or string is rejected. When no
        volume is given, use the clock's current volume setting.
        """
        if volume is None:
            return await self.get_volume_level()
        if isinstance(volume, bool) or not isinstance(volume, int):
            raise ValueError(f"volume must be an integer 0-100, got {volume!r}")
        if not 0 <= volume <= 100:
            raise ValueError(f"volume must be between 0 and 100, got {volume}")
        return volume

    async def play_alarm_sound(
        self, sound_name: str, volume: int | None = None
    ) -> None:
        """Play an alarm sound.

        volume is an integer 0-100. If it isn't given, the clock's current volume
        setting is used.
        """
        data = {
            "sound": sound_name,
            "vol": await self._get_alarm_sound_volume(volume),
        }
        await self._call_api("alarms/sounds/play", "POST", data)

    async def stop_alarm_sound(self, volume: int | None = None) -> None:
        """Stop playing an alarm sound.

        The clock requires "vol" on a stop request too. If volume isn't given, the
        clock's current volume setting is used.
        """
        data = {"sound": "stop", "vol": await self._get_alarm_sound_volume(volume)}
        await self._call_api("alarms/sounds/play", "POST", data)

    async def get_alexa_ascending_alarms_mode(self) -> bool:
        """Get whether alexa should use ascending alarms."""
        ascending = await self._call_api("alexa/ascending")
        return ascending["ascending"]

    async def set_alexa_ascending_alarms_mode(self, on: bool) -> bool:
        """Set whether alexa should use ascending alarms."""
        data = {"ascending": on}
        ascending = await self._call_api("alexa/ascending", "PUT", data)
        return ascending["ascending"]

    async def get_light_sensor_value(self) -> int:
        """Get the light sensor value (0-65535)."""
        light_sensor = await self._call_api("hardware/light-sensor")
        return light_sensor["sensor"]

    async def get_is_in_day_mode(self) -> str:
        """Get the day/night mode status."""
        daymode = await self._call_api("hardware/day-mode")
        return daymode["isDayMode"]

    async def get_day_to_night_transition_value(self) -> int:
        """Get the day to night transition value (0-65535)."""
        transition = await self._call_api("hardware/high-to-low-transition")
        return transition["transition"]

    async def set_day_to_night_transition_value(self, transition: int) -> int:
        """Set the day to night transition value (0-65535)."""
        transition = await self._call_api(
            "hardware/high-to-low-transition", "PUT", {"transition": int(transition)}
        )
        return transition["transition"]

    async def get_night_to_day_transition_value(self) -> int:
        """Get the night to day transition value (0-65535)."""
        transition = await self._call_api("hardware/low-to-high-transition")
        return transition["transition"]

    async def set_night_to_day_transition_value(self, transition: int) -> int:
        """Set the night to day transition value (0-65535)."""
        transition = await self._call_api(
            "hardware/low-to-high-transition", "PUT", {"transition": int(transition)}
        )
        return transition["transition"]

    async def get_day_display_brightness(self) -> int:
        """Get day display brightness (0-100)."""
        brightness = await self._call_api("hardware/high-display-brightness")
        return brightness["brightness"]

    async def set_day_display_brightness(self, brightness: int) -> int:
        """Set day display brightness (0-100)."""
        data = {"brightness": brightness}
        brightness = await self._call_api(
            "hardware/high-display-brightness", "PUT", data
        )
        return brightness["brightness"]

    async def get_day_button_brightness(self) -> int:
        """Get day button brightness (0-100)."""
        brightness = await self._call_api("hardware/high-button-brightness")
        return brightness["brightness"]

    async def set_day_button_brightness(self, brightness: int) -> int:
        """Set day button brightness (0-100)."""
        data = {"brightness": brightness}
        brightness = await self._call_api(
            "hardware/high-button-brightness", "PUT", data
        )
        return brightness["brightness"]

    async def get_night_display_brightness(self) -> int:
        """Get night display brightness (0-100)."""
        brightness = await self._call_api("hardware/low-display-brightness")
        return brightness["brightness"]

    async def set_night_display_brightness(self, brightness: int) -> int:
        """Set night display brightness (0-100)."""
        data = {"brightness": brightness}
        brightness = await self._call_api(
            "hardware/low-display-brightness", "PUT", data
        )
        return brightness["brightness"]

    async def get_night_button_brightness(self) -> int:
        """Get night button brightness (0-100)."""
        brightness = await self._call_api("hardware/low-button-brightness")
        return brightness["brightness"]

    async def set_night_button_brightness(self, brightness: int) -> int:
        """Set night button brightness (0-100)."""
        data = {"brightness": brightness}
        brightness = await self._call_api("hardware/low-button-brightness", "PUT", data)
        return brightness["brightness"]

    async def get_sync_button_display_brightness(self) -> bool:
        """Get whether button and display brightness are display brightness."""
        sync_button_display_brightness = await self._call_api(
            "hardware/sync-button-display-brightness"
        )
        return sync_button_display_brightness["sync"]

    async def set_sync_button_display_brightness(self, enabled: bool) -> bool:
        """Set whether button and display brightness are display brightness."""
        data = {"sync": enabled}
        sync_button_display_brightness = await self._call_api(
            "hardware/sync-button-display-brightness", "PUT", data
        )
        return sync_button_display_brightness["sync"]

    async def get_sync_day_night_color(self) -> bool:
        """Get whether day and night color color are always day color."""
        sync_day_night_color = await self._call_api("hardware/sync-high-low-color")
        return sync_day_night_color["sync"]

    async def set_sync_day_night_color(self, enabled: bool) -> bool:
        """Set whether day and night color color are always day color."""
        data = {"sync": enabled}
        sync_day_night_color = await self._call_api(
            "hardware/sync-high-low-color", "PUT", data
        )
        return sync_day_night_color["sync"]

    async def get_sync_button_display_color(self) -> bool:
        """Get whether button and display color are always display color."""
        sync_button_display_color = await self._call_api(
            "hardware/sync-button-display-color"
        )
        return sync_button_display_color["sync"]

    async def set_sync_button_display_color(self, enabled: bool) -> bool:
        """Set whether button and display color are always display color."""
        data = {"sync": enabled}
        sync_button_display_color = await self._call_api(
            "hardware/sync-button-display-color", "PUT", data
        )
        return sync_button_display_color["sync"]

    async def get_day_display_color(self) -> Color:
        """Get day display color."""
        color = await self._call_api("hardware/high-display-color")
        return Color.from_list(color["color"])

    async def set_day_display_color(self, color: Color) -> Color:
        """Set day display color."""
        data = {"color": color.to_list()}
        color = await self._call_api("hardware/high-display-color", "PUT", data)
        return Color.from_list(color["color"])

    async def get_night_display_color(self) -> Color:
        """Get night display color."""
        color = await self._call_api("hardware/low-display-color")
        return Color.from_list(color["color"])

    async def set_night_display_color(self, color: Color) -> Color:
        """Set night display color."""
        data = {"color": color.to_list()}
        color = await self._call_api("hardware/low-display-color", "PUT", data)
        return Color.from_list(color["color"])

    async def get_day_button_color(self) -> Color:
        """Get day button color."""
        color = await self._call_api("hardware/high-button-color")
        return Color.from_list(color["color"])

    async def set_day_button_color(self, color: Color) -> Color:
        """Set day button color."""
        data = {"color": color.to_list()}
        color = await self._call_api("hardware/high-button-color", "PUT", data)
        return Color.from_list(color["color"])

    async def get_night_button_color(self) -> Color:
        """Get night button color."""
        color = await self._call_api("hardware/low-button-color")
        return Color.from_list(color["color"])

    async def set_night_button_color(self, color: Color) -> Color:
        """Set night button color."""
        data = {"color": color.to_list()}
        color = await self._call_api("hardware/low-button-color", "PUT", data)
        return Color.from_list(color["color"])

    async def get_weather_configuration(self) -> WeatherConfiguration:
        """Get the weather configuration for the device."""
        weather_config = await self._call_api("software/weather")
        return WeatherConfiguration.from_dict(weather_config)

    async def set_weather_configuration(
        self,
        enabled: bool | None = None,
        location: str | None = None,
        mode: WeatherMode | None = None,
    ) -> WeatherConfiguration:
        """
        Set the weather configuration for the device.

        If any input is None, the existing value for that parameter will be used.
        """
        if any(attr is None for attr in (enabled, location, mode)):
            weather_config_dict = await self._call_api("software/weather")
            weather_config = WeatherConfiguration.from_dict(weather_config_dict)
            if enabled is not None:
                weather_config.enabled = enabled
            if location is not None:
                weather_config.location = location
            if mode is not None:
                weather_config.mode = mode
        else:
            weather_config = WeatherConfiguration(enabled, location, mode)

        data = weather_config.to_dict()
        weather_config_dict = await self._call_api("software/weather", "PUT", data)
        return WeatherConfiguration.from_dict(weather_config_dict)

    async def get_weather_wake_up_time(self) -> time:
        """Get the time at which the weather will be retrieved."""
        weather_wake_up_time_str = await self._call_api("software/weather-wakeup-time")
        time_parts = weather_wake_up_time_str["weatherwakeuptime"].split(":")
        return time(hour=int(time_parts[0]), minute=int(time_parts[1]))

    async def set_weather_wake_up_time(self, wake_up_time: time) -> time:
        """Set the time at which the weather will be retrieved."""
        data = {"weatherwakeuptime": wake_up_time.strftime("%H:%M")}
        weather_wake_up_time_str = await self._call_api(
            "software/weather-wakeup-time", "PUT", data
        )
        time_parts = weather_wake_up_time_str["weatherwakeuptime"].split(":")
        return time(hour=int(time_parts[0]), minute=int(time_parts[1]))

    async def get_is_connected_to_alexa(self) -> bool:
        """Get whether the device is connected to Alexa."""
        lwa_status = await self._call_api("alexa/lwa-status")
        return lwa_status["status"]

    async def get_is_alexa_tap_to_talk_tone_enabled(self) -> bool:
        """Return whether tone will play after Alexa tap to talk button is pressed."""
        tap_talk_tone_enabled = await self._call_api("alexa/tap-talk-tone")
        return tap_talk_tone_enabled["tone"]

    async def set_alexa_tap_to_talk_tone_enabled(self, enabled: bool) -> bool:
        """Set whether tone will play after Alexa tap to talk button is pressed."""
        data = {"tone": enabled}
        tap_talk_tone_enabled = await self._call_api("alexa/tap-talk-tone", "PUT", data)
        return tap_talk_tone_enabled["tone"]

    async def get_is_alexa_wake_word_tone_enabled(self) -> bool:
        """Return whether tone will play after Alexa wake word is spoken."""
        wake_word_tone_enabled = await self._call_api("alexa/wake-word-tone")
        return wake_word_tone_enabled["tone"]

    async def set_alexa_wake_word_tone_enabled(self, enabled: bool) -> bool:
        """Set whether tone will play after Alexa wake word is spoken."""
        data = {"tone": enabled}
        wake_word_tone_enabled = await self._call_api(
            "alexa/wake-word-tone", "PUT", data
        )
        return wake_word_tone_enabled["tone"]

    async def set_rainbow_mode(self, rc: RainbowConfiguration) -> RainbowConfiguration:
        """Set Whether Clock face is displayed in cycling rainbow colors"""
        data = {"speed": rc.to_dict()["speed"], "mode": rc.to_dict()["mode"]}

        rainbow_mode = await self._call_api("software/use-rainbow-display", "PUT", data)
        return RainbowConfiguration.from_dict(rainbow_mode)

    async def get_rainbow_mode(self) -> RainbowConfiguration:
        """Get Whether Clock face is displayed in cycling rainbow colors"""

        rainbow_mode = await self._call_api("software/use-rainbow-display", "GET")
        return RainbowConfiguration.from_dict(rainbow_mode)

    async def get_smart_button_color(self, button_num: int) -> Color:
        """Get the color of the specified smart button."""
        smart_button_config = await self.get_smart_button_configuration(button_num)
        return smart_button_config.color

    async def get_smart_button_configuration(
        self, button_num: int
    ) -> SmartButtonConfiguration:
        """Get the smart button configuration for the device."""
        smart_button_config_dict = await self._call_api(f"hardware/button{button_num}")
        return SmartButtonConfiguration.from_dict(smart_button_config_dict)

    async def set_smart_button_configuration(
        self,
        button_num: int,
        url: str | None = None,
        command: str | None = None,
        color: Color | None = None,
    ) -> SmartButtonConfiguration:
        """Set the smart button configuration for the device."""
        if url is None or color is None or command is None:
            smart_button_config = await self.get_smart_button_configuration(button_num)
        else:
            smart_button_config = SmartButtonConfiguration("", "HA", Color(0, 0, 0))
        if url is not None:
            smart_button_config.webhook_url = url
        if color is not None:
            smart_button_config.color = color
        if command is not None:
            smart_button_config.command = command
        smart_button_config_dict = await self._call_api(
            f"hardware/button{button_num}",
            "PUT",
            {**smart_button_config.to_dict(), "data": str(button_num)},
        )
        return SmartButtonConfiguration.from_dict(smart_button_config_dict)

    async def set_main_display_text(self, mdt: MainDisplayText) -> MainDisplayText:
        """Set Scrolling Text on the main display."""
        data = mdt.to_dict()
        params = await self._call_api("hardware/display-text", "PUT", data)
        return MainDisplayText.from_dict(params)

    async def set_mini_display_number(
        self, mdn: MiniDisplayNumber
    ) -> MiniDisplayNumber:
        """Set number on the mini display."""
        data = mdn.to_dict()
        params = await self._call_api("hardware/small-display-digits", "PUT", data)
        return MiniDisplayNumber.from_dict(params)

    async def set_light_bar_effect(
        self, lbde: LightBarDisplayEffect
    ) -> LightBarDisplayEffect:
        """Set light bar display effect."""
        data = lbde.to_dict()
        params = await self._call_api("hardware/display-dots", "PUT", data)
        return LightBarDisplayEffect.from_dict(params)

    async def get_all_data(self) -> dict[str, Any]:
        """Get all data from the device."""
        # tuple of tuples to map keys to all get methods to simplify any integration
        # logic
        data_mapping = (
            (ATTR_WIFI, self.get_wifi_status()),
            (ATTR_TIME_MODE, self.get_time_mode()),
            (ATTR_TIMEZONE, self.get_timezone()),
            (ATTR_TIME_OFFSET, self.get_offset()),
            (ATTR_USE_COLON, self.get_use_colon_mode()),
            (ATTR_COLON_BLINK, self.get_colon_blink_mode()),
            (ATTR_USE_LEADING_ZERO, self.get_use_leading_zero_mode()),
            (ATTR_USE_FADE_TIME, self.get_use_fade_time()),
            (ATTR_DISPLAY_SECONDS, self.get_display_seconds_mode()),
            (ATTR_VOLUME_LEVEL, self.get_volume_level()),
            (ATTR_SOUND_PRESET, self.get_sound_preset()),
            (ATTR_SOUND_PRESET_MODE, self.get_sound_preset_mode()),
            (ATTR_ALARMS, self.get_all_alarms()),
            (ATTR_ALARM_SOUNDS, self.get_alarm_sounds()),
            (ATTR_ALEXA_USE_ASCENDING_ALARMS, self.get_alexa_ascending_alarms_mode()),
            (ATTR_LIGHT_SENSOR_VALUE, self.get_light_sensor_value()),
            (ATTR_IS_IN_DAY_MODE, self.get_is_in_day_mode()),
            (
                ATTR_DAY_TO_NIGHT_TRANSITION_VALUE,
                self.get_day_to_night_transition_value(),
            ),
            (
                ATTR_NIGHT_TO_DAY_TRANSITION_VALUE,
                self.get_night_to_day_transition_value(),
            ),
            (ATTR_DAY_DISPLAY_BRIGHTNESS, self.get_day_display_brightness()),
            (ATTR_DAY_BUTTON_BRIGHTNESS, self.get_day_button_brightness()),
            (ATTR_NIGHT_DISPLAY_BRIGHTNESS, self.get_night_display_brightness()),
            (ATTR_NIGHT_BUTTON_BRIGHTNESS, self.get_night_button_brightness()),
            (
                ATTR_SYNC_BUTTON_AND_DISPLAY_BRIGHTNESS,
                self.get_sync_button_display_brightness(),
            ),
            (ATTR_SYNC_BUTTON_AND_DISPLAY_COLOR, self.get_sync_button_display_color()),
            (ATTR_SYNC_DAY_AND_NIGHT_COLOR, self.get_sync_day_night_color()),
            (ATTR_DAY_DISPLAY_COLOR, self.get_day_display_color()),
            (ATTR_DAY_BUTTON_COLOR, self.get_day_button_color()),
            (ATTR_NIGHT_DISPLAY_COLOR, self.get_night_display_color()),
            (ATTR_NIGHT_BUTTON_COLOR, self.get_night_button_color()),
            (ATTR_WEATHER, self.get_weather_configuration()),
            (ATTR_WEATHER_WAKE_UP_TIME, self.get_weather_wake_up_time()),
            (ATTR_CONNECTED_TO_ALEXA, self.get_is_connected_to_alexa()),
            (
                ATTR_ALEXA_TAP_TO_TALK_TONE_ENABLED,
                self.get_is_alexa_tap_to_talk_tone_enabled(),
            ),
            (
                ATTR_ALEXA_WAKE_WORD_TONE_ENABLED,
                self.get_is_alexa_wake_word_tone_enabled(),
            ),
            *(
                (
                    f"{ATTR_SMART_BUTTON_COLOR}_{i}",
                    self.get_smart_button_color(i),
                )
                for i in range(1, 3)
            ),
        )

        # Splits tuple of key and function tuples into keys and functions iterators
        keys, coros = zip(*data_mapping)
        # Executes all functions and joins the result with the key in a tuple so we can
        # create a dict from it
        data = {key: result for key, result in zip(keys, await asyncio.gather(*coros))}
        return data
