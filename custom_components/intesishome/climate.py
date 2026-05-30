"""Support for IntesisHome Smart AC Controllers."""
from __future__ import annotations

import logging

from pyintesishome import IntesisBase

from homeassistant import config_entries, core
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    SWING_OFF,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# MODE MAPS
# ─────────────────────────────────────────────
MAP_IH_TO_HVAC_MODE = {
    "auto": HVACMode.AUTO,
    "cool": HVACMode.COOL,
    "dry":  HVACMode.DRY,
    "fan":  HVACMode.FAN_ONLY,
    "heat": HVACMode.HEAT,
    "off":  HVACMode.OFF,
}
MAP_HVAC_MODE_TO_IH = {v: k for k, v in MAP_IH_TO_HVAC_MODE.items()}

# ─────────────────────────────────────────────
# PRESET MAPS
# ─────────────────────────────────────────────
MAP_IH_TO_PRESET_MODE = {
    "eco":      PRESET_ECO,
    "comfort":  PRESET_COMFORT,
    "powerful": PRESET_BOOST,
}
MAP_PRESET_MODE_TO_IH = {v: k for k, v in MAP_IH_TO_PRESET_MODE.items()}

# ─────────────────────────────────────────────
# SWING / VANE MAPS
# ─────────────────────────────────────────────
_VANE_POSITIONS = {
    SWING_OFF: "auto/stop",
    "Swing": "swing",
    **{f"Position{n}": f"manual{n}" for n in range(1, 10)},
}
MAP_SWING_TO_IH = _VANE_POSITIONS
MAP_HORIZONTAL_SWING_TO_IH = _VANE_POSITIONS
MAP_IH_TO_SWING = {v: k for k, v in _VANE_POSITIONS.items()}

# ─────────────────────────────────────────────
# MODE → MDI ICON MAP
# Changes the entity icon in HA based on active HVAC mode
# ─────────────────────────────────────────────
MAP_STATE_ICONS = {
    HVACMode.COOL:     "mdi:snowflake",
    HVACMode.DRY:      "mdi:water-off",
    HVACMode.FAN_ONLY: "mdi:fan",
    HVACMode.HEAT:     "mdi:white-balance-sunny",
    HVACMode.AUTO:     "mdi:cached",
}


def _swing_names_from_controller_list(ih_positions: list[str] | None) -> list[str]:
    """Translate IH swing positions to HA-facing names, skipping unknowns."""
    if not ih_positions:
        return []
    names: list[str] = []
    for ih in ih_positions:
        ha = MAP_IH_TO_SWING.get(ih)
        if ha is None:
            _LOGGER.warning("Unexpected swing position reported by device: %s", ih)
            continue
        names.append(ha)
    return names


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create climate entities from config entry."""
    controller: IntesisBase = hass.data[DOMAIN][config_entry.entry_id]["controller"]
    ih_devices = controller.get_devices() or {}
    async_add_entities(
        [
            IntesisAC(ih_device_id, device, controller)
            for ih_device_id, device in ih_devices.items()
        ],
        update_before_add=True,
    )


class IntesisAC(ClimateEntity):
    """Represents an IntesisHome air conditioning device."""

    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, ih_device_id, ih_device, controller) -> None:
        """Initialise the climate entity."""
        self._controller: IntesisBase = controller
        self._device_id: str = ih_device_id
        self._ih_device: dict = ih_device
        self._device_name: str = ih_device.get("name")
        self._device_type: str = controller.device_type
        self._connected: bool = False
        self._setpoint_step: float = 1.0
        self._current_temp: float = None
        self._max_temp: float = None
        self._attr_hvac_modes: list[HVACMode] = []
        self._min_temp: int = None
        self._target_temp: float = None
        self._outdoor_temp: float = None
        self._hvac_mode: HVACMode = None
        self._preset: str = None
        self._preset_list: list[str] = [PRESET_ECO, PRESET_COMFORT, PRESET_BOOST]
        self._run_hours: int = None
        self._rssi = None
        self._swing_list: list[str] = []
        self._swing_horizontal_list: list[str] = []
        self._vvane: str = None
        self._hvane: str = None
        self._power: bool = False
        self._fan_speed = None
        self._attr_supported_features = 0
        self._power_consumption_heat = None
        self._power_consumption_cool = None

        # Turn on / off
        self._attr_supported_features |= ClimateEntityFeature.TURN_ON
        self._attr_supported_features |= ClimateEntityFeature.TURN_OFF

        # Temperature setpoint
        if controller.has_setpoint_control(ih_device_id):
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE

        # Swing (vertical + horizontal)
        self._swing_list = _swing_names_from_controller_list(
            controller.get_vertical_swing_list(ih_device_id)
        )
        self._swing_horizontal_list = _swing_names_from_controller_list(
            controller.get_horizontal_swing_list(ih_device_id)
        )
        if self._swing_list:
            self._attr_supported_features |= ClimateEntityFeature.SWING_MODE
        if self._swing_horizontal_list:
            self._attr_supported_features |= ClimateEntityFeature.SWING_HORIZONTAL_MODE

        # Fan speed
        self._fan_modes = controller.get_fan_speed_list(ih_device_id)
        if self._fan_modes:
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE

        # Preset
        if ih_device.get("climate_working_mode"):
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE

        # HVAC modes — dynamically read from device, mapped to HA enums
        if modes := controller.get_mode_list(ih_device_id):
            for mode in modes:
                if mode in MAP_IH_TO_HVAC_MODE:
                    self._attr_hvac_modes.append(MAP_IH_TO_HVAC_MODE[mode])
                else:
                    _LOGGER.warning("Unexpected HVAC mode from device: %s", mode)
        self._attr_hvac_modes.append(HVACMode.OFF)

    # ─────────────────────────────────────────
    # HA LIFECYCLE
    # ─────────────────────────────────────────

    async def async_added_to_hass(self) -> None:
        """Register update callback once entity is live."""
        _LOGGER.debug("Added climate device with state: %s", repr(self._ih_device))
        self._controller.add_update_callback(self.async_update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Deregister callback — do NOT stop the shared controller here."""
        self._controller.remove_update_callback(self.async_update_callback)

    async def async_update_callback(self, device_id=None) -> None:
        """Push HA state update when the controller reports a change."""
        if self._controller and not self._controller.is_connected and self._connected:
            self._connected = False
            _LOGGER.info("Connection to %s API was lost", self._device_type)
        elif self._controller and self._controller.is_connected and not self._connected:
            self._connected = True
            _LOGGER.debug("Connection to %s API was restored", self._device_type)

        if not device_id or self._device_id == device_id:
            self.async_schedule_update_ha_state(True)

    async def async_update(self) -> None:
        """Pull current state from the shared controller dictionary."""
        self._connected   = self._controller.is_connected
        self._current_temp = self._controller.get_temperature(self._device_id)
        self._fan_speed   = self._controller.get_fan_speed(self._device_id)
        self._power       = self._controller.is_on(self._device_id)
        self._min_temp    = self._controller.get_min_setpoint(self._device_id)
        self._max_temp    = self._controller.get_max_setpoint(self._device_id)
        self._rssi        = self._controller.get_rssi(self._device_id)
        self._run_hours   = self._controller.get_run_hours(self._device_id)
        self._target_temp = self._controller.get_setpoint(self._device_id)
        self._outdoor_temp = self._controller.get_outdoor_temperature(self._device_id)

        mode = self._controller.get_mode(self._device_id)
        self._hvac_mode = MAP_IH_TO_HVAC_MODE.get(mode)

        preset = self._controller.get_preset_mode(self._device_id)
        self._preset = MAP_IH_TO_PRESET_MODE.get(preset)

        self._vvane = self._controller.get_vertical_swing(self._device_id)
        self._hvane = self._controller.get_horizontal_swing(self._device_id)

        self._power_consumption_heat = self._controller.get_heat_power_consumption(
            self._device_id
        )
        self._power_consumption_cool = self._controller.get_cool_power_consumption(
            self._device_id
        )

        # Re-apply feature flags if they weren't set yet
        if not self._attr_supported_features:
            if self._fan_modes:
                self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
            if self._controller.has_setpoint_control(self._device_id):
                self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            if self._swing_list:
                self._attr_supported_features |= ClimateEntityFeature.SWING_MODE
            if self._swing_horizontal_list:
                self._attr_supported_features |= ClimateEntityFeature.SWING_HORIZONTAL_MODE
            if self._ih_device.get("climate_working_mode"):
                self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE

    # ─────────────────────────────────────────
    # COMMANDS
    # ─────────────────────────────────────────

    def _expect_ack(self, success: bool, description: str) -> None:
        """Raise HomeAssistantError when a controller command is not acknowledged."""
        if not success:
            raise HomeAssistantError(
                f"IntesisHome did not acknowledge {description}"
            )

    async def async_turn_on(self) -> None:
        """Turn device on."""
        ok = await self._controller.set_power_on(self._device_id)
        self._expect_ack(ok, "power on")
        self._power = True

    async def async_turn_off(self) -> None:
        """Turn device off."""
        ok = await self._controller.set_power_off(self._device_id)
        self._expect_ack(ok, "power off")
        self._power = False

    async def async_toggle(self) -> None:
        """Toggle power."""
        if not self._controller.is_on(self._device_id):
            await self.async_turn_on()
        else:
            await self.async_turn_off()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature (and optionally switch mode at the same time)."""
        if hvac_mode := kwargs.get(ATTR_HVAC_MODE):
            await self.async_set_hvac_mode(hvac_mode)

        if temperature := kwargs.get(ATTR_TEMPERATURE):
            _LOGGER.debug("Setting %s to %s °C", self._device_type, temperature)
            ok = await self._controller.set_temperature(self._device_id, temperature)
            self._expect_ack(ok, f"temperature {temperature}")
            self._target_temp = temperature

        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC operation mode."""
        _LOGGER.debug("Setting %s to %s", self._device_type, hvac_mode)

        if hvac_mode == HVACMode.OFF:
            ok = await self._controller.set_power_off(self._device_id)
            self._expect_ack(ok, "power off")
            self._power = False
            self.async_write_ha_state()
            return

        # Power on first if needed
        if not self._controller.is_on(self._device_id):
            ok = await self._controller.set_power_on(self._device_id)
            self._expect_ack(ok, "power on")
            self._power = True

        ok = await self._controller.set_mode(
            self._device_id, MAP_HVAC_MODE_TO_IH[hvac_mode]
        )
        self._expect_ack(ok, f"HVAC mode {hvac_mode}")

        # Re-send setpoint — mode changes can reset it on some devices
        if self._target_temp:
            await self._controller.set_temperature(self._device_id, self._target_temp)

        self._hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan speed."""
        ok = await self._controller.set_fan_speed(self._device_id, fan_mode)
        self._expect_ack(ok, f"fan mode {fan_mode!r}")
        self._fan_speed = fan_mode
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode (eco / comfort / powerful)."""
        ih_preset = MAP_PRESET_MODE_TO_IH.get(preset_mode)
        ok = await self._controller.set_preset_mode(self._device_id, ih_preset)
        self._expect_ack(ok, f"preset {preset_mode!r}")

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set vertical vane position."""
        if ih_swing := MAP_SWING_TO_IH.get(swing_mode):
            ok = await self._controller.set_vertical_vane(self._device_id, ih_swing)
            self._expect_ack(ok, f"vertical vane {swing_mode!r}")

    async def async_set_swing_horizontal_mode(self, swing_mode: str) -> None:
        """Set horizontal vane position."""
        if ih_swing := MAP_SWING_TO_IH.get(swing_mode):
            ok = await self._controller.set_horizontal_vane(self._device_id, ih_swing)
            self._expect_ack(ok, f"horizontal vane {swing_mode!r}")

    # ─────────────────────────────────────────
    # PROPERTIES
    # ─────────────────────────────────────────

    @property
    def name(self) -> str:
        """Return device name."""
        return self._device_name

    @property
    def unique_id(self) -> str:
        """Return unique device ID."""
        return self._device_id

    @property
    def icon(self) -> str | None:
        """Return MDI icon matching the active HVAC mode.

        Returns None when off so HA falls back to the default thermostat icon.
        """
        if self._power:
            return MAP_STATE_ICONS.get(self._hvac_mode)
        return None

    @property
    def temperature_unit(self) -> str:
        """IntesisHome API always uses Celsius internally."""
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode; OFF when unit is powered down."""
        if self._power:
            return self._hvac_mode
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        return self._current_temp

    @property
    def target_temperature(self) -> float | None:
        """Return setpoint; hidden for fan-only and off states."""
        if self._power and self.hvac_mode not in [HVACMode.FAN_ONLY, HVACMode.OFF]:
            return self._target_temp
        return None

    @property
    def target_temperature_step(self) -> float:
        return self._setpoint_step

    @property
    def min_temp(self) -> float | None:
        return self._min_temp

    @property
    def max_temp(self) -> float | None:
        return self._max_temp

    @property
    def fan_mode(self) -> str | None:
        return self._fan_speed

    @property
    def fan_modes(self) -> list[str] | None:
        return self._fan_modes

    @property
    def swing_mode(self) -> str | None:
        if self._vvane is None:
            return None
        return MAP_IH_TO_SWING.get(self._vvane)

    @property
    def swing_modes(self) -> list[str]:
        return self._swing_list

    @property
    def swing_horizontal_mode(self) -> str | None:
        if self._hvane is None:
            return None
        return MAP_IH_TO_SWING.get(self._hvane)

    @property
    def swing_horizontal_modes(self) -> list[str]:
        return self._swing_horizontal_list

    @property
    def preset_mode(self) -> str | None:
        return self._preset

    @property
    def preset_modes(self) -> list[str]:
        return self._preset_list

    @property
    def extra_state_attributes(self) -> dict:
        """Expose outdoor temp and power consumption as extra attributes."""
        attrs = {}
        if self._outdoor_temp is not None:
            attrs["outdoor_temp"] = self._outdoor_temp
        if self._power_consumption_heat:
            attrs["power_consumption_heat_kw"] = round(
                self._power_consumption_heat / 1000, 1
            )
        if self._power_consumption_cool:
            attrs["power_consumption_cool_kw"] = round(
                self._power_consumption_cool / 1000, 1
            )
        return attrs

    @property
    def available(self) -> bool:
        """Mark unavailable only when connection has explicitly failed."""
        return self._connected or self._connected is None

    @property
    def should_poll(self) -> bool:
        return True
