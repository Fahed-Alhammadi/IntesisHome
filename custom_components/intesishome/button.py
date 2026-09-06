"""Buttons for IntesisHome devices (filter maintenance reset)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pyintesishome import IntesisBase

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN, IntesisConfigEntry

# Push-based integration: no need to serialise entity updates.
PARALLEL_UPDATES = 0

# filter_due_hours (UID 184) has no COMMAND_MAP entry in pyintesishome, so
# clearing the "needs cleaning" flag after maintenance requires writing the
# raw datapoint via the library's private _set_value() — the same approach
# the upstream jnimmo/hass-intesishome integration uses for this button.
_FILTER_DUE_HOURS_UID = 184


@dataclass(frozen=True, kw_only=True)
class IntesisButtonEntityDescription(ButtonEntityDescription):
    """Describes an IntesisHome button."""

    press_fn: Callable[[IntesisBase, str], Awaitable[bool]]
    required_property: str


BUTTON_TYPES: tuple[IntesisButtonEntityDescription, ...] = (
    IntesisButtonEntityDescription(
        key="reset_filter",
        translation_key="reset_filter",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:filter-remove",
        required_property="filter_clean",
        press_fn=lambda controller, device_id: controller._set_value(
            device_id, _FILTER_DUE_HOURS_UID, 0
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: IntesisConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create button entities for each device that supports them."""
    controller = config_entry.runtime_data
    ih_devices = controller.get_devices() or {}

    entities: list[IntesisButton] = []
    for device_id, device in ih_devices.items():
        for description in BUTTON_TYPES:
            if description.required_property in device:
                entities.append(
                    IntesisButton(controller, device_id, device, description)
                )

    async_add_entities(entities)


class IntesisButton(ButtonEntity):
    """A maintenance action button for an IntesisHome device."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: IntesisButtonEntityDescription

    def __init__(
        self,
        controller: IntesisBase,
        device_id: str,
        device: dict,
        description: IntesisButtonEntityDescription,
    ) -> None:
        """Initialise the button."""
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

    async def async_press(self) -> None:
        """Reset the filter-clean flag after the filter has been cleaned."""
        ok = await self.entity_description.press_fn(self._controller, self._device_id)
        if not ok:
            raise HomeAssistantError("IntesisHome did not acknowledge filter reset")
