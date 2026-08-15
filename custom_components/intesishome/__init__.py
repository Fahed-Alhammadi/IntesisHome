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

# How often to verify the cloud connection is still alive (see health check).
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
        """Recover a dead cloud connection.

        pyintesishome retries dropped connections itself with backoff, but it
        stops retrying permanently after an authentication error from the
        cloud. Calling connect() here is a no-op while its own reconnect is
        in progress; once it has given up, this either revives the
        connection or surfaces the auth failure so the reauth flow can
        prompt for a new password instead of leaving entities unavailable.
        """
        if controller.is_connected:
            return
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT):
                await controller.connect()
        except TimeoutError:
            _LOGGER.debug("IntesisHome still unreachable: timed out connecting")
        except IHAuthenticationError:
            _LOGGER.error(
                "IntesisHome credentials are no longer valid; starting reauth"
            )
            entry.async_start_reauth(hass)
        except IHConnectionError as exc:
            _LOGGER.debug("IntesisHome still unreachable: %s", exc)

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
