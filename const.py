"""Constants for the Greenhouse Controller integration."""

DOMAIN = "greenhouse"

# Configuration Keys (Entities externes : Capteurs et Relais de commande)
CONF_SENSOR_TEMP_IN = "sensor_temp_in"
CONF_SENSOR_TEMP_OUT = "sensor_temp_out"
CONF_BINARY_SENSOR_RAIN = "binary_sensor_rain"
CONF_BINARY_SENSOR_WIND = "binary_sensor_wind"

CONF_SWITCH_OPEN = "switch_open"
CONF_SWITCH_CLOSE = "switch_close"

# Parameters
CONF_TEMP_TARGET_MIN = "temperature_target_min"
CONF_TEMP_TARGET_MAX = "temperature_target_max"
CONF_SWITCH_ENABLE_REGULATION = "enable_regulation_on_change"
CONF_PI_TICK_INTERVAL = "pi_tick_interval"
CONF_KP = "kp"
CONF_KI = "ki"
CONF_INTEGRAL_MAX = "integral_max"
CONF_STEP_SIZE = "step_size_pct"
CONF_TIME_MAX_OPEN = "time_max_to_open"
CONF_TIME_OVERLOAD = "time_max_to_open_overload"
CONF_MAX_VENT = "ouverture_max_vent"
CONF_MAX_PLUIE = "ouverture_max_pluie"
CONF_DELAY_AFTER_RAIN = "delay_after_rain"
CONF_DELAY_AFTER_WIND = "delay_after_wind"

# Defaults
DEFAULT_TEMP_MIN = 20.0
DEFAULT_TEMP_MAX = 30.0
DEFAULT_PI_TICK_INTERVAL = 60  # en secondes (1 minute par défaut)
DEFAULT_KP = 8.0
DEFAULT_KI = 0.1
DEFAULT_INTEGRAL_MAX = 600.0
DEFAULT_STEP_SIZE = 25
DEFAULT_TIME_MAX_OPEN = 20.0
DEFAULT_TIME_OVERLOAD = 5.0
DEFAULT_MAX_VENT = 8
DEFAULT_MAX_PLUIE = 15
DEFAULT_DELAY_AFTER_RAIN = 15.0
DEFAULT_DELAY_AFTER_WIND = 30.0