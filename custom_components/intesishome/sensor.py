"""Sensors for IntesisHome devices (outdoor temperature, power consumption)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pyintesishome import IntesisBase

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, IntesisConfigEntry


def _to_kw(value: float | None) -> float | None:
    """Convert a raw watt reading to kilowatts."""
    if value is None:
        return None
    return round(value / 1000, 1)


@dataclass(frozen=True, kw_only=True)
class IntesisSensorEntityDescription(SensorEntityDescription):
    """Describes an IntesisHome sensor."""

    value_fn: Callable[[IntesisBase, str], float | None]


SENSOR_TYPES: tuple[IntesisSensorEntityDescription, ...] = (
    IntesisSensorEntityDescription(
        key="outdoor_temp",
        translation_key="outdoor_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda controller, device_id: controller.get_outdoor_temperature(
            device_id
        ),
    ),
    IntesisSensorEntityDescription(
        key="power_consumption_heat",
        translation_key="power_consumption_heat",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda controller, device_id: _to_kw(
            controller.get_heat_power_consumption(device_id)
        ),
    ),
    IntesisSensorEntityDescription(
        key="power_consumption_cool",
        translation_key="power_consumption_cool",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda controller, device_id: _to_kw(
            controller.get_cool_power_consumption(device_id)
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: IntesisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensor entities for each device that reports a value."""
    controller = config_entry.runtime_data
    ih_devices = controller.get_devices() or {}

    entities: list[IntesisSensor] = []
    for device_id, device in ih_devices.items():
        for description in SENSOR_TYPES:
            # Only create the sensor if the device actually reports this value.
            if description.value_fn(controller, device_id) is not None:
                entities.append(
                    IntesisSensor(controller, device_id, device, description)
                )

    async_add_entities(entities)


class IntesisSensor(SensorEntity):
    """Representation of an IntesisHome diagnostic/measurement sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: IntesisSensorEntityDescription

    def __init__(
        self,
        controller: IntesisBase,
        device_id: str,
        device: dict,
        description: IntesisSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        self._controller = controller
        self._device_id = device_id
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.get("name"),
            manufacturer="Intesis",
            model=controller.device_type,
        )

    @property
    def native_value(self) -> float | None:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self._controller, self._device_id)

    @property
    def available(self) -> bool:
        """Return True while the controller has a live connection."""
        return self._controller.is_connected

    async def async_added_to_hass(self) -> None:
        """Register update callback once entity is live."""
        self._controller.add_update_callback(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Deregister callback — do NOT stop the shared controller here."""
        self._controller.remove_update_callback(self.async_update_callback)

    async def async_update_callback(self, device_id=None) -> None:
        """Push HA state update when the controller reports a change."""
        if not device_id or self._device_id == device_id:
            self.async_write_ha_state()
