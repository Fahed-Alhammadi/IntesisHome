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
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IntesisConfigEntry
from .entity import IntesisEntity

# Push-based integration: no need to serialise entity updates.
PARALLEL_UPDATES = 0


def _to_kw(value: float | None) -> float | None:
    """Convert a raw watt reading to kilowatts."""
    if value is None:
        return None
    return round(value / 1000, 1)


def _to_number(value) -> float | None:
    """Coerce API values that may arrive as strings into numbers."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
    IntesisSensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        value_fn=lambda controller, device_id: _to_number(
            controller.get_rssi(device_id)
        ),
    ),
    IntesisSensorEntityDescription(
        key="error_code",
        translation_key="error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
        # A bare vendor error number means little on its own; the "problem"
        # binary sensor is the user-facing signal, so keep this off by default.
        entity_registry_enabled_default=False,
        icon="mdi:alert-circle-outline",
        # Reads the raw register rather than controller.get_error(): that
        # helper's ERROR_MAP maps code 0 to a truthy "no abnormality" string,
        # which would make this sensor never read as "no error" (0/None).
        value_fn=lambda controller, device_id: _to_number(
            controller.get_device_property(device_id, "error_code")
        ),
    ),
    IntesisSensorEntityDescription(
        key="filter_due_hours",
        translation_key="filter_due_hours",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:filter-outline",
        value_fn=lambda controller, device_id: _to_number(
            controller.get_device_property(device_id, "filter_due_hours")
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


class IntesisSensor(IntesisEntity, SensorEntity):
    """Representation of an IntesisHome diagnostic/measurement sensor."""

    entity_description: IntesisSensorEntityDescription

    def __init__(
        self,
        controller: IntesisBase,
        device_id: str,
        device: dict,
        description: IntesisSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(controller, device_id, device)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self._controller, self._device_id)
