"""Binary sensors for IntesisHome devices (alarm, filter, connectivity)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pyintesishome import IntesisBase

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import IntesisConfigEntry
from .entity import IntesisEntity

# Push-based integration: no need to serialise entity updates.
PARALLEL_UPDATES = 0

# Sentinel for entities derived from the session itself rather than a device
# datapoint (e.g. connectivity), so they are always created.
_NO_PROPERTY_REQUIRED = None


@dataclass(frozen=True, kw_only=True)
class IntesisBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an IntesisHome binary sensor."""

    value_fn: Callable[[IntesisBase, str], bool | None]
    required_property: str | None = _NO_PROPERTY_REQUIRED
    # True for entities that must keep reporting while the cloud session is down.
    always_available: bool = False


BINARY_SENSOR_TYPES: tuple[IntesisBinarySensorEntityDescription, ...] = (
    IntesisBinarySensorEntityDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        required_property="alarm_status",
        value_fn=lambda controller, device_id: bool(
            controller.get_device_property(device_id, "alarm_status")
        ),
    ),
    IntesisBinarySensorEntityDescription(
        key="filter_clean",
        translation_key="filter_clean",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:air-filter",
        required_property="filter_clean",
        value_fn=lambda controller, device_id: bool(
            controller.get_device_property(device_id, "filter_clean")
        ),
    ),
    IntesisBinarySensorEntityDescription(
        key="connectivity",
        translation_key="connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        # A connectivity sensor that goes unavailable exactly when the
        # connection drops reports nothing at the moment it matters most.
        always_available=True,
        value_fn=lambda controller, device_id: controller.is_available,
    ),
)


def _has_device_property(controller: IntesisBase, device_id: str, prop: str) -> bool:
    """Return True when the device advertises the given raw property.

    Needed instead of checking value_fn() for None: bool(None) is a valid
    "False" reading, so that check alone can't tell "unsupported" apart from
    "supported and currently false".
    """
    return prop in (controller.get_device(device_id) or {})


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: IntesisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create binary sensor entities for each device that supports them."""
    controller = config_entry.runtime_data
    ih_devices = controller.get_devices() or {}

    entities: list[IntesisBinarySensor] = []
    for device_id, device in ih_devices.items():
        for description in BINARY_SENSOR_TYPES:
            if description.required_property is _NO_PROPERTY_REQUIRED or (
                _has_device_property(controller, device_id, description.required_property)
            ):
                entities.append(
                    IntesisBinarySensor(controller, device_id, device, description)
                )

    async_add_entities(entities)


class IntesisBinarySensor(IntesisEntity, BinarySensorEntity):
    """Representation of an IntesisHome diagnostic binary sensor."""

    entity_description: IntesisBinarySensorEntityDescription

    def __init__(
        self,
        controller: IntesisBase,
        device_id: str,
        device: dict,
        description: IntesisBinarySensorEntityDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(controller, device_id, device)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the current reading."""
        return self.entity_description.value_fn(self._controller, self._device_id)

    @property
    def available(self) -> bool:
        """Return True while the controller has a live connection."""
        if self.entity_description.always_available:
            return True
        return super().available
