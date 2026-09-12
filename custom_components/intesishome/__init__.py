"""The IntesisHome integration."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from pyintesishome import IHAuthenticationError, IHConnectionError, IntesisHome
from pyintesishome.const import DEVICE_INTESISHOME

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


async def async_setup_entry(hass: HomeAssistant, entry: IntesisConfigEntry) -> bool:
    """Set up IntesisHome from a config entry."""
    # Older entries were created before the service selector existed. Keep
    # their historical IntesisHome behaviour until the user selects a
    # different cloud service during reauth.
    device_type = entry.data.get(CONF_DEVICE, DEVICE_INTESISHOME)
    controller = IntesisHome(
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
    # command through this lock (see climate.py/button.py) avoids that race
    # instead of working around pyintesishome's internals.
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
