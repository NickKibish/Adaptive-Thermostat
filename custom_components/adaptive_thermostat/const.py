"""Constants for Adaptive Thermostat integration."""
import math

DOMAIN = "adaptive_thermostat"

# Configuration keys
CONF_REAL_THERMOSTAT = "real_thermostat"
CONF_TEMP_SENSOR = "temperature_sensor"
CONF_PRICE_SENSOR = "price_sensor"  # Optional
CONF_TOLERANCE = "tolerance"
CONF_BASE_SHIFT = "base_shift"
CONF_HIGH_SETPOINT = "high_setpoint"
CONF_LOW_SETPOINT = "low_setpoint"
CONF_MAX_PRICE_SHIFT = "max_price_shift"  # Configurable
CONF_PRICE_STEEPNESS = "price_steepness"  # Configurable

# Default values
DEFAULT_TOLERANCE = 0.5  # °C
DEFAULT_BASE_SHIFT = 0.0  # °C
DEFAULT_HIGH_SETPOINT = 35.0  # °C - forces heating ON
DEFAULT_LOW_SETPOINT = 5.0  # °C - forces heating OFF
DEFAULT_MAX_PRICE_SHIFT = 3.0  # °C - configurable in advanced settings
DEFAULT_PRICE_STEEPNESS = 1.5  # configurable in advanced settings

# Update interval
DEFAULT_UPDATE_INTERVAL = 30  # seconds - for temperature sensor polling

# Entry data keys
ENTRY_DATA_COORDINATOR = "coordinator"

# Attributes
ATTR_CURRENT_SHIFT = "current_shift"
ATTR_PRICE_DIFF_PERCENT = "price_diff_percent"
ATTR_HEATING_STATE = "heating_state"


def price_based_shift_percent(
    price_diff_percent: float,
    max_shift: float = DEFAULT_MAX_PRICE_SHIFT,
    steepness: float = DEFAULT_PRICE_STEEPNESS,
) -> float:
    """
    Calculate temperature shift based on price difference in percent.

    Args:
        price_diff_percent: +49 = 49% more expensive, -30 = 30% cheaper
        max_shift: Maximum shift in °C
        steepness: Curve steepness

    Returns:
        Temperature shift in °C (negative = delay heating, positive = advance heating)
    """
    p = price_diff_percent / 100.0
    return -max_shift * math.tanh(steepness * p)
