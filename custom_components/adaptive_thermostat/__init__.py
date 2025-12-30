"""Adaptive Thermostat integration."""
from __future__ import annotations
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    ENTRY_DATA_COORDINATOR,
    CONF_TEMP_SENSOR,
    CONF_PRICE_SENSOR,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Thermostat from config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create coordinator to poll sensors
    coordinator = AdaptiveThermostatCoordinator(hass, entry)

    # Initial refresh
    await coordinator.async_config_entry_first_refresh()

    # Start price sensor listener
    await coordinator.async_start()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = {
        ENTRY_DATA_COORDINATOR: coordinator,
    }

    # Forward to climate platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload config entry."""
    # Stop coordinator (including price sensor listener)
    coordinator = hass.data[DOMAIN][entry.entry_id][ENTRY_DATA_COORDINATOR]
    await coordinator.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class AdaptiveThermostatCoordinator(DataUpdateCoordinator):
    """Coordinator to poll temperature sensor and listen to price sensor changes."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.entry = entry
        self.temp_sensor_id = entry.data[CONF_TEMP_SENSOR]
        self.price_sensor_id = entry.data.get(CONF_PRICE_SENSOR)
        self._price_listener_unsubscribe = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

    async def async_start(self) -> None:
        """Start listening to price sensor changes."""
        if self.price_sensor_id:
            from homeassistant.helpers.event import async_track_state_change_event

            @callback
            def price_changed(event):
                """Handle price sensor state change."""
                _LOGGER.debug("Price sensor changed, triggering update")
                # Trigger coordinator update which will call _async_update_data
                self.hass.async_create_task(self.async_request_refresh())

            self._price_listener_unsubscribe = async_track_state_change_event(
                self.hass, [self.price_sensor_id], price_changed
            )

    async def async_stop(self) -> None:
        """Stop listening to price sensor changes."""
        if self._price_listener_unsubscribe:
            self._price_listener_unsubscribe()
            self._price_listener_unsubscribe = None

    async def _async_update_data(self) -> dict:
        """Fetch sensor data."""
        data = {}

        # Get temperature sensor state (polled every 30s)
        temp_state = self.hass.states.get(self.temp_sensor_id)
        if temp_state is None:
            _LOGGER.warning("Temperature sensor %s not found", self.temp_sensor_id)
            data["temperature"] = None
        else:
            try:
                data["temperature"] = float(temp_state.state)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid temperature value: %s", temp_state.state)
                data["temperature"] = None

        # Get price sensor state (updated on state change)
        data["price_diff_percent"] = None
        if self.price_sensor_id:
            price_state = self.hass.states.get(self.price_sensor_id)
            if price_state is not None:
                try:
                    data["price_diff_percent"] = float(price_state.state)
                except (ValueError, TypeError):
                    _LOGGER.warning("Invalid price value: %s", price_state.state)

        return data
