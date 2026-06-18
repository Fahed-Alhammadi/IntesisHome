"""The IntesisHome integration."""
from __future__ import annotations

import logging

from pyintesishome import IHAuthenticationError, IHConnectionError, IntesisHome
from pyintesishome.const import DEVICE_INTESISHOME

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

DOMAIN = "intesishome"
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: IntesisConfigEntry) -> bool:
    """Unload a config entry and stop the controller."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.stop()
    return unload_ok
