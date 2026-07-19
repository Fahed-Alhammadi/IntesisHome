"""The IntesisHome integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from pyintesishome import IHAuthenticationError, IHConnectionError, IntesisHome
from pyintesishome.const import DEVICE_INTESISHOME

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

DOMAIN = "intesishome"
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

# How often to verify the cloud connection is still alive (see health check).
HEALTH_CHECK_INTERVAL = timedelta(minutes=5)

_LOGGER = logging.getLogger(__name__)

type IntesisConfigEntry = ConfigEntry[IntesisHome]


async def async_setup_entry(hass: HomeAssistant, entry: IntesisConfigEntry) -> bool:
    """Set up IntesisHome from a config entry."""
    controller = IntesisHome(
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        hass.loop,
        websession=async_get_clientsession(hass),
        device_type=DEVICE_INTESISHOME,
    )

    try:
        await controller.connect()
    except IHAuthenticationError as exc:
        _LOGGER.error("Invalid IntesisHome credentials")
        raise ConfigEntryAuthFailed from exc
    except IHConnectionError as exc:
        _LOGGER.error("Error connecting to IntesisHome: %s", exc)
        raise ConfigEntryNotReady from exc

    if not controller.get_devices():
        await controller.stop()
        _LOGGER.error("No devices returned from IntesisHome API")
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
            await controller.connect()
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
