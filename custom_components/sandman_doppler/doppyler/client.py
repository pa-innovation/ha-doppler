"""Main module."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import Any, Callable

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    BASE_SANDMAN_API_URL,
    DEFAULT_CLOUD_API_SEMAPHORE_LIMIT,
    DEFAULT_HEADERS,
    DEFAULT_LOCAL_API_SEMAPHORE_LIMIT,
    DEFAULT_TIMEOUT,
    LOGIN_URL,
    REFRESH_URL,
    THINGS_URL,
)
from .exceptions import (
    BadRequestException,
    CantConnectException,
    DopplerException,
    ExpiredNonce,
    InvalidDataReturned,
    SerialMismatch,
    UnauthorizedException,
    UnknownException,
)
from .model.doppler import Doppler, DopplerDeviceInfo

# Fields of the clock's `device` reply (see DopplerDeviceInfo)
_DEVICE_INFO_KEYS = (
    "serialNum",
    "mfgrName",
    "modelNum",
    "firmware",
    "hardware",
    "software",
)

_LOGGER = logging.getLogger(__name__)

# Keys (compared case-insensitively) whose values must never reach logs or
# exception messages: the account password, cloud tokens and the clock's local key.
_REDACTED_KEYS = frozenset({"password", "accesstoken", "refreshtoken", "localkey"})
_REDACTED = "**REDACTED**"


def _redact(value: Any) -> Any:
    """Return a copy of a request/response body with secret values replaced."""
    if isinstance(value, dict):
        return {
            k: (
                _REDACTED
                if isinstance(k, str) and k.lower() in _REDACTED_KEYS
                else _redact(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


class DopplerClient:
    """Class to interact with Doppler API."""

    def __init__(
        self,
        email: str | None,
        password: str | None,
        timeout: int = DEFAULT_TIMEOUT,
        client_session: ClientSession | None = None,
        local_control: bool = True,
        cloud_api_semaphore_limit: int = DEFAULT_CLOUD_API_SEMAPHORE_LIMIT,
        local_api_semaphore_limit: int = DEFAULT_LOCAL_API_SEMAPHORE_LIMIT,
    ) -> None:
        """Initialize client."""
        self._cloud_api_semaphore = asyncio.Semaphore(cloud_api_semaphore_limit)
        self._local_api_semaphore_limit = local_api_semaphore_limit
        self._token_event = asyncio.Event()
        self._token_event.set()

        self._removed_listeners: list[Callable[[Doppler], None]] = []
        self._added_listeners: list[Callable[[Doppler], None]] = []
        self.email = email
        self._password = password
        self.application_name = "SANDMANDOPPLER"
        self.application_version = "154"
        self._session = client_session
        self._timeout = ClientTimeout(timeout)
        self.devices: dict[str, Doppler] = {}

        # Login attributes
        self._device_type = "PHONE"
        self._os_type = "ANDROID"
        self._device_model = "PIXEL"
        self._os_version = "9"
        self._device_id = "12345678"

        # Token management
        self._access_token = None
        self._access_token_expires = None
        self._token_for_refresh = None

        # Local Control info
        self.local_control = local_control

        self._loop = asyncio.get_running_loop()

    def _call_listeners(self, doppler: Doppler, listeners: list) -> None:
        """Call all listeners."""
        for listener in listeners.copy():
            if asyncio.iscoroutinefunction(listener):
                self._loop.create_task(listener(doppler))
            else:
                listener(doppler)

    async def request(
        self,
        url: str,
        method: str = "GET",
        data: dict = None,
        headers: dict = None,
        verify_ssl: bool = True,
    ) -> dict:
        """Make a request to the Doppler API.

        TLS certificates are verified unless verify_ssl is False, which is only for
        the clock's local API (its certificate can't be verified).
        """
        if self._session:
            return await self._request(
                self._session,
                url,
                method=method,
                data=data,
                headers=headers,
                verify_ssl=verify_ssl,
            )

        async with ClientSession(timeout=self._timeout) as session:
            return await self._request(
                session,
                url,
                method=method,
                data=data,
                headers=headers,
                verify_ssl=verify_ssl,
            )

    async def _request(
        self,
        session: ClientSession,
        url: str,
        method: str = "GET",
        data: dict = None,
        headers: dict = None,
        verify_ssl: bool = True,
    ) -> dict:
        """
        Make a request to the Doppler API.

        Session has to be provided.
        """
        resp_data: dict | str
        # Request and response bodies can carry the account password, tokens and
        # the clock's local key, so only redacted copies go to logs and exceptions.
        safe_data = _redact(data)
        _LOGGER.debug("Initiate request via %s %s with %s", method, url, safe_data)
        try:
            resp = await session.request(
                method,
                url,
                json=data,
                headers={**(headers or {}), **DEFAULT_HEADERS},
                timeout=self._timeout,
                # None uses aiohttp's default certificate verification.
                ssl=None if verify_ssl else False,
            )
        except (asyncio.TimeoutError, ClientError) as err:
            raise CantConnectException(
                f"{type(err).__name__} on {method} {url}"
            ) from err
        else:
            try:
                resp_data = await resp.json(content_type=None)
            except JSONDecodeError:
                resp_data = await resp.text()

            safe_resp_data = _redact(resp_data)
            _LOGGER.debug("Received via %s %s: %s", method, url, safe_resp_data)

            if resp.status in (200, 201):
                if isinstance(resp_data, str):
                    # Some endpoints (e.g. alarms/sounds/play on firmware 0.1714)
                    # answer a successful request with the plain-text body "OK".
                    if resp_data.strip() == "OK":
                        return {}
                    raise InvalidDataReturned(safe_resp_data, method, url, safe_data)
                return resp_data

            if resp.status == 400:
                raise BadRequestException(safe_resp_data, method, url, safe_data)
            if resp.status in (401, 403):
                raise UnauthorizedException(safe_resp_data, method, url, safe_data)
            if resp.status == 410:
                raise ExpiredNonce(safe_resp_data, method, url, safe_data)
            if resp.status == 408:
                raise CantConnectException(safe_resp_data, method, url, safe_data)
            raise UnknownException(safe_resp_data, method, url, safe_data)

    async def get_token(self) -> None:
        """Get token."""
        self._token_event.clear()
        auth_payload = {
            "authenticationDetails": {
                "applicationId": self.application_name,
                "email": self.email,
                "password": self._password,
            },
            "deviceDetails": {
                "applicationVersion": self.application_version,
                "deviceId": self._device_id,
                "deviceModel": self._device_model,
                "deviceType": self._device_type,
                "osType": self._os_type,
                "osVersion": self._os_version,
                "timezone": {
                    "currentTimeInClientInMilliseconds": 0,
                    "offsetFromUTCInMilliseconds": 0,
                    "timeZoneId": "UTC",
                },
            },
        }
        data = await self.request(LOGIN_URL, "POST", auth_payload)
        self._access_token = data["accessToken"]
        self._access_token_expires = datetime.utcnow() + timedelta(
            seconds=data["expiresIn"]
        )
        self._token_for_refresh = data["refreshToken"]
        self._token_event.set()

    async def _refresh_token(self) -> None:
        """Refresh token."""
        self._token_event.clear()
        refresh_payload = {"refreshToken": self._token_for_refresh}
        data = await self.request(REFRESH_URL, "PUT", refresh_payload)
        self._access_token = data["accessToken"]
        self._access_token_expires = datetime.utcnow() + timedelta(
            seconds=data["expiresIn"]
        )
        self._token_for_refresh = data["refreshToken"]
        self._token_event.set()

    async def _call_copilot_api(self, url: str, method: str = "GET", data: dict = None):
        """
        Call Copilot API.

        Automatically retrieves a new token if needed.
        """
        # Bounds the number of concurrent requests to the cloud API
        async with self._cloud_api_semaphore:
            # Blocks other calls while getting a token
            await self._token_event.wait()
            if not self._access_token:
                await self.get_token()
            elif datetime.utcnow() > self._access_token_expires:
                await self._refresh_token()

            try:
                return await self.request(
                    url, method, data, {"Authorization": f"Bearer {self._access_token}"}
                )
            except UnauthorizedException:
                self._access_token = None
                return await self._call_copilot_api(url, method, data)

    def on_device_removed(
        self, callback: Callable[[Doppler], None]
    ) -> Callable[[None], None]:
        """Register a callback for when a device is removed."""
        self._removed_listeners.append(callback)

        def unsubscribe() -> None:
            """Unsubscribe listeners."""
            if callback in self._removed_listeners:
                self._removed_listeners.remove(callback)

        return unsubscribe

    def on_device_added(
        self, callback: Callable[[Doppler], None]
    ) -> Callable[[None], None]:
        """Register a callback for when a device is added."""
        self._added_listeners.append(callback)

        def unsubscribe() -> None:
            """Unsubscribe listeners."""
            if callback in self._added_listeners:
                self._added_listeners.remove(callback)

        return unsubscribe

    async def call_cloud_api(
        self,
        dsn: str,
        endpoint: str,
        method: str = "GET",
        data: dict = None,
    ) -> dict:
        """Make a request to the cloud Doppler API."""
        return await self._call_copilot_api(
            f"{BASE_SANDMAN_API_URL}/{dsn}/{endpoint}", method, data
        )

    async def _add_or_update_device(self, device_dict: dict[str, Any]) -> None:
        """Add new device or update existing device."""
        dsn = device_dict["info"]["physicalId"]
        name = device_dict["info"]["name"]
        try:
            device_info, local_info = await asyncio.gather(
                self.call_cloud_api(dsn, "device"),
                self.call_cloud_api(dsn, "localkey"),
            )
        except DopplerException:
            return

        if dsn in self.devices:
            self.devices[dsn].update(name, device_info, local_info)
        else:
            self.devices[dsn] = Doppler(
                self,
                name,
                device_info,
                local_info,
                self.local_control,
                self._local_api_semaphore_limit,
            )

    async def add_local_device(
        self,
        dsn: str,
        name: str,
        host: str,
        port: int,
        local_key: str,
        notify: bool = True,
    ) -> Doppler:
        """Add a clock that is controlled only on the local network.

        Needs no Sandman account or cloud: the clock's local key is supplied by the
        caller (it is stored on the clock itself) and the device info comes from the
        clock's own `device` endpoint. Raises a DopplerException if the clock can't
        be reached, rejects the key or reports another serial number. With
        notify=False the device-added listeners are not called.
        """
        placeholder: dict[str, str] = dict.fromkeys(_DEVICE_INFO_KEYS, "")
        placeholder["serialNum"] = dsn
        local_info = {"localkey": local_key, "ipAddie": host, "port": port}
        doppler = Doppler(
            self,
            name,
            placeholder,
            local_info,
            True,
            self._local_api_semaphore_limit,
        )
        try:
            device_info = await doppler.get_device_info()
        except BadRequestException as err:
            # The clock answers 400 DOPPLER_ID_NOT_FOUND ("Illegal DSN") when the
            # serial in the URL isn't its own; the check is case-sensitive.
            if "DOPPLER_ID_NOT_FOUND" in str(err):
                raise SerialMismatch(
                    "the clock does not have this serial number", "GET", "nonce", None
                ) from err
            raise
        if not isinstance(device_info, dict) or any(
            key not in device_info for key in _DEVICE_INFO_KEYS
        ):
            raise InvalidDataReturned(
                "device info is missing fields", "GET", "device", None
            )
        if str(device_info["serialNum"]).lower() != dsn.lower():
            raise SerialMismatch(
                "clock reported a different serial number", "GET", "device", None
            )
        # Keep the serial exactly as the clock reports it.
        doppler.device_info = DopplerDeviceInfo(device_info)
        dsn = doppler.dsn

        is_new = dsn not in self.devices
        self.devices[dsn] = doppler
        if is_new and notify:
            self._call_listeners(doppler, self._added_listeners)
        return doppler

    async def get_devices(self) -> dict[str, Doppler]:
        """Get all devices for account."""
        data = (await self._call_copilot_api(THINGS_URL)).get("things", [])
        existing_dsns = set(self.devices)

        await asyncio.gather(
            *(self._add_or_update_device(device_dict) for device_dict in data)
        )

        # Call add listeners for any DSNs that are now in the dictionary
        for dsn in set(self.devices) - existing_dsns:
            self._call_listeners(self.devices[dsn], self._added_listeners)

        # Call remove listeners for any DSNs that are no longer in the devices update
        for dsn in existing_dsns - {device["info"]["physicalId"] for device in data}:
            self._call_listeners(self.devices.pop(dsn), self._removed_listeners)

        return self.devices
