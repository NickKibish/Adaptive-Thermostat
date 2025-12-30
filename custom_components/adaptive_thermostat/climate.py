"""Climate platform for Adaptive Thermostat."""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENTRY_DATA_COORDINATOR,
    CONF_REAL_THERMOSTAT,
    CONF_TEMP_SENSOR,
    CONF_PRICE_SENSOR,
    CONF_TOLERANCE,
    CONF_BASE_SHIFT,
    CONF_HIGH_SETPOINT,
    CONF_LOW_SETPOINT,
    CONF_MAX_PRICE_SHIFT,
    CONF_PRICE_STEEPNESS,
    DEFAULT_MAX_PRICE_SHIFT,
    DEFAULT_PRICE_STEEPNESS,
    ATTR_CURRENT_SHIFT,
    ATTR_PRICE_DIFF_PERCENT,
    ATTR_HEATING_STATE,
    price_based_shift_percent,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Thermostat climate entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id][ENTRY_DATA_COORDINATOR]

    async_add_entities([AdaptiveThermostat(coordinator, entry)], True)


class AdaptiveThermostat(CoordinatorEntity, ClimateEntity):
    """Adaptive thermostat climate entity."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize adaptive thermostat."""
        super().__init__(coordinator)

        self._entry = entry
        self._real_thermostat_id = entry.data[CONF_REAL_THERMOSTAT]
        self._temp_sensor_id = entry.data[CONF_TEMP_SENSOR]
        self._price_sensor_id = entry.data.get(CONF_PRICE_SENSOR)

        # Configuration
        self._tolerance = entry.data.get(CONF_TOLERANCE)
        self._base_shift = entry.data.get(CONF_BASE_SHIFT)
        self._high_setpoint = entry.data.get(CONF_HIGH_SETPOINT)
        self._low_setpoint = entry.data.get(CONF_LOW_SETPOINT)
        self._max_price_shift = entry.data.get(CONF_MAX_PRICE_SHIFT, DEFAULT_MAX_PRICE_SHIFT)
        self._price_steepness = entry.data.get(CONF_PRICE_STEEPNESS, DEFAULT_PRICE_STEEPNESS)

        # State tracking
        self._target_temperature = 20.0  # Default target
        self._hvac_mode = HVACMode.HEAT
        self._is_heating = False  # Track actual heating state for hysteresis

        # Entity attributes
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"
        self._attr_name = f"Adaptive {self._real_thermostat_id.split('.')[-1].replace('_', ' ').title()}"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_target_temperature_step = 0.5
        self._attr_min_temp = 5.0
        self._attr_max_temp = 35.0

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature from sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("temperature")

    @property
    def target_temperature(self) -> float:
        """Return target temperature."""
        return self._target_temperature

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        return self._hvac_mode

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if self._hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        return HVACAction.HEATING if self._is_heating else HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        attrs = {
            ATTR_CURRENT_SHIFT: self._calculate_total_shift(),
            ATTR_HEATING_STATE: "heating" if self._is_heating else "idle",
        }

        if self.coordinator.data and self.coordinator.data.get("price_diff_percent") is not None:
            attrs[ATTR_PRICE_DIFF_PERCENT] = self.coordinator.data["price_diff_percent"]

        return attrs

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        self._target_temperature = temperature
        await self._async_control_heating()
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode not in self._attr_hvac_modes:
            return

        self._hvac_mode = hvac_mode

        if hvac_mode == HVACMode.OFF:
            # Turn off heating
            await self._async_set_real_thermostat(self._low_setpoint)
            self._is_heating = False
        else:
            # Recalculate heating state
            await self._async_control_heating()

        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from coordinator."""
        self.hass.async_create_task(self._async_control_heating())
        super()._handle_coordinator_update()

    async def _async_control_heating(self) -> None:
        """Apply hysteresis control logic."""
        if self._hvac_mode == HVACMode.OFF:
            return

        current_temp = self.current_temperature
        if current_temp is None:
            _LOGGER.warning("Temperature sensor unavailable - maintaining current state")
            return

        total_shift = self._calculate_total_shift()
        target = self._target_temperature
        tolerance = self._tolerance

        # Hysteresis control logic
        should_heat = None

        if current_temp < target - tolerance + total_shift:
            # Below lower threshold - turn ON
            should_heat = True
        elif current_temp > target + tolerance + total_shift:
            # Above upper threshold - turn OFF
            should_heat = False
        else:
            # In dead zone - maintain current state (hysteresis)
            should_heat = self._is_heating

        # Only change if state differs
        if should_heat != self._is_heating:
            self._is_heating = should_heat
            setpoint = self._high_setpoint if should_heat else self._low_setpoint
            await self._async_set_real_thermostat(setpoint)

            _LOGGER.info(
                "Heating state changed: %s (current: %.1f°C, target: %.1f°C, shift: %.2f°C)",
                "ON" if should_heat else "OFF",
                current_temp,
                target,
                total_shift,
            )

    def _calculate_total_shift(self) -> float:
        """Calculate total temperature shift (base + price-based)."""
        total_shift = self._base_shift

        if self._price_sensor_id and self.coordinator.data:
            price_diff = self.coordinator.data.get("price_diff_percent")
            if price_diff is not None:
                price_shift = price_based_shift_percent(
                    price_diff,
                    self._max_price_shift,
                    self._price_steepness,
                )
                total_shift += price_shift

        return total_shift

    async def _async_set_real_thermostat(self, temperature: float) -> None:
        """Set real thermostat setpoint."""
        try:
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {
                    "entity_id": self._real_thermostat_id,
                    "temperature": temperature,
                },
                blocking=True,
            )
            _LOGGER.debug(
                "Set %s to %.1f°C",
                self._real_thermostat_id,
                temperature,
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to set %s temperature: %s",
                self._real_thermostat_id,
                err,
            )
