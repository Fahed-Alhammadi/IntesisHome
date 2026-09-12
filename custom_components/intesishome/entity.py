"""Shared entity base class for IntesisHome platforms."""
from __future__ import annotations

from pyintesishome import IntesisBase

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import DOMAIN


class IntesisEntity(Entity):
    """Common wiring for the sensor/binary_sensor/button platforms.

    Climate entities track availability themselves (see IntesisAC in
    climate.py) and so keep their own implementation rather than using this
    base class.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, controller: IntesisBase, device_id: str, device: dict) -> None:
        """Initialise shared entity state."""
        self._controller = controller
        self._device_id = device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.get("name"),
            manufacturer="Intesis",
            model=controller.device_type,
        )

    @property
    def available(self) -> bool:
        """Return True while the controller has a live connection."""
        return self._controller.is_available

    async def async_added_to_hass(self) -> None:
        """Register update callback once entity is live."""
        self._controller.add_update_callback(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Deregister callback — do NOT stop the shared controller here."""
        self._controller.remove_update_callback(self.async_update_callback)

    async def async_update_callback(self, device_id: str | None = None) -> None:
        """Push HA state update when the controller reports a change."""
        if not device_id or self._device_id == device_id:
            self.async_write_ha_state()
