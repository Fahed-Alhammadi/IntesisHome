"""The IntesisHome integration."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging

from pyintesishome import IHAuthenticationError, IHConnectionError, IntesisHome
from pyintesishome.const import DEVICE_INTESISHOME, PORTAL_URL

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

DOMAIN = "intesishome"
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

# How often to check for a permanently-rejected credential (see health check).
HEALTH_CHECK_INTERVAL = timedelta(minutes=5)

# Bounds a single connect() attempt. pyintesishome's own HTTP/socket calls
# have no timeout of their own (aiohttp's ~5 min default applies at best), so
# without this a stalled cloud endpoint can make every retry — at setup and
# at each health check — ride out a long stall instead of failing fast.
CONNECT_TIMEOUT = 30

_LOGGER = logging.getLogger(__name__)

type IntesisConfigEntry = ConfigEntry[IntesisHome]


async def async_send_command(
    controller: IntesisHome, send: Callable[[], Awaitable[bool]]
) -> bool:
    """Run one controller SET under command_lock (see async_setup_entry)."""
    async with controller.command_lock:
        return await send()


class _IntesisHome(IntesisHome):
    """IntesisHome that sends commands via the web portal, skipping the socket.

    Since IntesisHome's September 2026 server change the command socket
    opens and authenticates fine, but SETs sent over it are never
    acknowledged — every command logged a "not acknowledged within 5.0s"
    warning and waited out the timeout before anything else could run. The
    brand's web portal still applies them. pyintesishome falls back to the
    portal only when the socket can't be opened, so report it as unopenable
    for services that have a portal: SETs then go straight there, with no
    wasted 5s, no warning, and no socket connects (which Intesis is known to
    blacklist IPs for). Services without a portal keep the socket path.
    """

    async def _ensure_socket(self) -> bool:
        if self._device_type in PORTAL_URL:
            return False
        return await super()._ensure_socket()


async def async_setup_entry(hass: HomeAssistant, entry: IntesisConfigEntry) -> bool:
    """Set up IntesisHome from a config entry."""
    # Older entries were created before the service selector existed. Keep
    # their historical IntesisHome behaviour until the user selects a
    # different cloud service during reauth.
    device_type = entry.data.get(CONF_DEVICE, DEVICE_INTESISHOME)
    controller = _IntesisHome(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        hass.loop,
        websession=async_get_clientsession(hass),
        device_type=device_type,
    )
    # pyintesishome opens one command socket per controller, shared by every
    # device/entity under this entry, and guards concurrent opens with a
    # plain bool (_connecting) rather than a lock — a second SET issued
    # while the first is still opening the socket (e.g. two quick taps on a
    # climate +/- stepper) skips the socket path entirely and falls back to
    # the (slower, separately fallible) web portal. Serialising every
    # command through this lock (via async_send_command below) avoids that
    # race instead of working around pyintesishome's internals.
    controller.command_lock = asyncio.Lock()

    try:
        async with asyncio.timeout(CONNECT_TIMEOUT):
            await controller.connect()
    except TimeoutError as exc:
        await controller.stop()
        _LOGGER.error("Timed out connecting to %s", device_type)
        raise ConfigEntryNotReady(f"Timed out connecting to {device_type}") from exc
    except IHAuthenticationError as exc:
        _LOGGER.error("Invalid credentials for %s", device_type)
        raise ConfigEntryAuthFailed from exc
    except IHConnectionError as exc:
        _LOGGER.error("Error connecting to %s: %s", device_type, exc)
        raise ConfigEntryNotReady from exc

    if not controller.get_devices():
        await controller.stop()
        _LOGGER.error("No devices returned from %s API", device_type)
        raise ConfigEntryNotReady("No devices returned from API")

    entry.runtime_data = controller

    async def _async_health_check(_now) -> None:
        """Start reauth once the cloud stops accepting these credentials.

        pyintesishome's background poller (added in 2.5.0, replacing the
        old push-socket auto-reconnect loop) retries connection errors
        forever on its own, but permanently retires itself once the cloud
        rejects the credentials. That is the one failure a retry can't
        fix, so this is what should trigger the reauth flow instead of
        leaving entities unavailable indefinitely.
        """
        if controller.authentication_failed:
            _LOGGER.error(
                "IntesisHome credentials are no longer valid; starting reauth"
            )
            entry.async_start_reauth(hass)

    entry.async_on_unload(
        async_track_time_interval(hass, _async_health_check, HEALTH_CHECK_INTERVAL)
    )

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await controller.stop()
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IntesisConfigEntry) -> bool:
    """Unload a config entry and stop the controller."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.stop()
    return unload_ok
