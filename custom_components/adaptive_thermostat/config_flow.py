"""Config flow for Adaptive Thermostat."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_REAL_THERMOSTAT,
    CONF_TEMP_SENSOR,
    CONF_PRICE_SENSOR,
    CONF_TOLERANCE,
    CONF_BASE_SHIFT,
    CONF_HIGH_SETPOINT,
    CONF_LOW_SETPOINT,
    CONF_MAX_PRICE_SHIFT,
    CONF_PRICE_STEEPNESS,
    DEFAULT_TOLERANCE,
    DEFAULT_BASE_SHIFT,
    DEFAULT_HIGH_SETPOINT,
    DEFAULT_LOW_SETPOINT,
    DEFAULT_MAX_PRICE_SHIFT,
    DEFAULT_PRICE_STEEPNESS,
)


class AdaptiveThermostatConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self._basic_config = {}

    async def async_step_user(self, user_input=None):
        """Handle initial step - basic configuration."""
        errors = {}

        if user_input is not None:
            # Validate entities exist
            errors = await self._validate_entities(user_input)

            if not errors:
                # Store basic config and proceed to advanced settings if price sensor configured
                self._basic_config = user_input

                if user_input.get(CONF_PRICE_SENSOR):
                    return await self.async_step_advanced()

                # No price sensor - skip advanced settings
                await self.async_set_unique_id(user_input[CONF_REAL_THERMOSTAT])
                self._abort_if_unique_id_configured()

                title = f"Adaptive {user_input[CONF_REAL_THERMOSTAT].split('.')[-1]}"
                return self.async_create_entry(title=title, data=user_input)

        # Define schema with entity selectors
        data_schema = vol.Schema({
            vol.Required(CONF_REAL_THERMOSTAT): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate")
            ),
            vol.Required(CONF_TEMP_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_PRICE_SENSOR): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_TOLERANCE, default=DEFAULT_TOLERANCE): cv.positive_float,
            vol.Optional(CONF_BASE_SHIFT, default=DEFAULT_BASE_SHIFT): vol.Coerce(float),
            vol.Optional(CONF_HIGH_SETPOINT, default=DEFAULT_HIGH_SETPOINT): cv.positive_float,
            vol.Optional(CONF_LOW_SETPOINT, default=DEFAULT_LOW_SETPOINT): cv.positive_float,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_advanced(self, user_input=None):
        """Advanced price shift configuration."""
        if user_input is not None:
            # Merge with basic config
            full_config = {**self._basic_config, **user_input}

            await self.async_set_unique_id(full_config[CONF_REAL_THERMOSTAT])
            self._abort_if_unique_id_configured()

            title = f"Adaptive {full_config[CONF_REAL_THERMOSTAT].split('.')[-1]}"
            return self.async_create_entry(title=title, data=full_config)

        # Only show if price sensor was configured
        if not self._basic_config.get(CONF_PRICE_SENSOR):
            # Skip advanced step - shouldn't happen but handle gracefully
            await self.async_set_unique_id(self._basic_config[CONF_REAL_THERMOSTAT])
            self._abort_if_unique_id_configured()
            title = f"Adaptive {self._basic_config[CONF_REAL_THERMOSTAT].split('.')[-1]}"
            return self.async_create_entry(title=title, data=self._basic_config)

        advanced_schema = vol.Schema({
            vol.Optional(CONF_MAX_PRICE_SHIFT, default=DEFAULT_MAX_PRICE_SHIFT): cv.positive_float,
            vol.Optional(CONF_PRICE_STEEPNESS, default=DEFAULT_PRICE_STEEPNESS): cv.positive_float,
        })

        return self.async_show_form(
            step_id="advanced",
            data_schema=advanced_schema,
            description_placeholders={
                "max_shift_desc": "Maximum temperature shift in °C (default: 3.0)",
                "steepness_desc": "Curve steepness factor (default: 1.5)",
            },
        )

    async def _validate_entities(self, user_input):
        """Validate that selected entities exist and are appropriate."""
        errors = {}

        # Check real thermostat exists
        if not self.hass.states.get(user_input[CONF_REAL_THERMOSTAT]):
            errors[CONF_REAL_THERMOSTAT] = "entity_not_found"

        # Check temperature sensor exists
        if not self.hass.states.get(user_input[CONF_TEMP_SENSOR]):
            errors[CONF_TEMP_SENSOR] = "entity_not_found"

        # Check optional price sensor if provided
        if CONF_PRICE_SENSOR in user_input and user_input[CONF_PRICE_SENSOR]:
            if not self.hass.states.get(user_input[CONF_PRICE_SENSOR]):
                errors[CONF_PRICE_SENSOR] = "entity_not_found"

        # Validate setpoint logic
        if user_input[CONF_HIGH_SETPOINT] <= user_input[CONF_LOW_SETPOINT]:
            errors[CONF_HIGH_SETPOINT] = "high_must_exceed_low"

        return errors

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow handler."""
        return AdaptiveThermostatOptionsFlow(config_entry)


class AdaptiveThermostatOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for reconfiguration."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options - allow changing tolerance, shifts, setpoints."""
        if user_input is not None:
            # Update config entry data with new values
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, **user_input}
            )
            return self.async_create_entry(title="", data={})

        current_data = self.config_entry.data

        options_schema_dict = {
            vol.Optional(
                CONF_TOLERANCE,
                default=current_data.get(CONF_TOLERANCE, DEFAULT_TOLERANCE)
            ): cv.positive_float,
            vol.Optional(
                CONF_BASE_SHIFT,
                default=current_data.get(CONF_BASE_SHIFT, DEFAULT_BASE_SHIFT)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_HIGH_SETPOINT,
                default=current_data.get(CONF_HIGH_SETPOINT, DEFAULT_HIGH_SETPOINT)
            ): cv.positive_float,
            vol.Optional(
                CONF_LOW_SETPOINT,
                default=current_data.get(CONF_LOW_SETPOINT, DEFAULT_LOW_SETPOINT)
            ): cv.positive_float,
        }

        # Add price shift parameters if price sensor is configured
        if current_data.get(CONF_PRICE_SENSOR):
            options_schema_dict[vol.Optional(
                CONF_MAX_PRICE_SHIFT,
                default=current_data.get(CONF_MAX_PRICE_SHIFT, DEFAULT_MAX_PRICE_SHIFT)
            )] = cv.positive_float
            options_schema_dict[vol.Optional(
                CONF_PRICE_STEEPNESS,
                default=current_data.get(CONF_PRICE_STEEPNESS, DEFAULT_PRICE_STEEPNESS)
            )] = cv.positive_float

        options_schema = vol.Schema(options_schema_dict)

        return self.async_show_form(step_id="init", data_schema=options_schema)
