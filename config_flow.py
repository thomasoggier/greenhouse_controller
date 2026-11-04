"""Config flow for Greenhouse Controller integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_SENSOR_TEMP_IN,
    CONF_SENSOR_TEMP_OUT,
    CONF_BINARY_SENSOR_RAIN,
    CONF_BINARY_SENSOR_WIND,
    CONF_SWITCH_OPEN,
    CONF_SWITCH_CLOSE,
    CONF_TEMP_TARGET_MIN,
    CONF_TEMP_TARGET_MAX,
    CONF_KP,
    CONF_KI,
    CONF_INTEGRAL_MAX,
    CONF_STEP_SIZE,
    CONF_TIME_MAX_OPEN,
    CONF_TIME_OVERLOAD,
    CONF_MAX_VENT,
    CONF_MAX_PLUIE,
    CONF_DELAY_AFTER_RAIN,
    CONF_DELAY_AFTER_WIND,
    CONF_PI_TICK_INTERVAL,
    DEFAULT_TEMP_MIN,
    DEFAULT_TEMP_MAX,
    DEFAULT_KP,
    DEFAULT_KI,
    DEFAULT_INTEGRAL_MAX,
    DEFAULT_STEP_SIZE,
    DEFAULT_TIME_MAX_OPEN,
    DEFAULT_TIME_OVERLOAD,
    DEFAULT_MAX_VENT,
    DEFAULT_MAX_PLUIE,
    DEFAULT_DELAY_AFTER_RAIN,
    DEFAULT_DELAY_AFTER_WIND,
    DEFAULT_PI_TICK_INTERVAL,
)

class GreenhouseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Greenhouse Controller."""

    VERSION = 1

    def __init__(self):
        self._data = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_parameters()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SENSOR_TEMP_IN): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_SENSOR_TEMP_OUT): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_BINARY_SENSOR_RAIN): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "input_boolean"])
                    ),
                    vol.Optional(CONF_BINARY_SENSOR_WIND): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "input_boolean"])
                    ),
                    vol.Required(CONF_SWITCH_OPEN): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch", "input_boolean"])
                    ),
                    vol.Required(CONF_SWITCH_CLOSE): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch", "input_boolean"])
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_parameters(self, user_input=None):
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="Greenhouse Controller", data=self._data)

        return self.async_show_form(
            step_id="parameters",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TEMP_TARGET_MIN, default=DEFAULT_TEMP_MIN): vol.Coerce(float),
                    vol.Required(CONF_TEMP_TARGET_MAX, default=DEFAULT_TEMP_MAX): vol.Coerce(float),
                    vol.Required(CONF_KP, default=DEFAULT_KP): vol.Coerce(float),
                    vol.Required(CONF_KI, default=DEFAULT_KI): vol.Coerce(float),
                    vol.Required(CONF_INTEGRAL_MAX, default=DEFAULT_INTEGRAL_MAX): vol.Coerce(float),
                    vol.Required(CONF_STEP_SIZE, default=DEFAULT_STEP_SIZE): vol.Coerce(int),
                    vol.Required(CONF_TIME_MAX_OPEN, default=DEFAULT_TIME_MAX_OPEN): vol.Coerce(float),
                    vol.Required(CONF_TIME_OVERLOAD, default=DEFAULT_TIME_OVERLOAD): vol.Coerce(float),
                    vol.Required(CONF_MAX_VENT, default=DEFAULT_MAX_VENT): vol.Coerce(int),
                    vol.Required(CONF_MAX_PLUIE, default=DEFAULT_MAX_PLUIE): vol.Coerce(int),
                    vol.Required(CONF_DELAY_AFTER_WIND, default=DEFAULT_DELAY_AFTER_WIND): vol.Coerce(float),
                    vol.Required(CONF_DELAY_AFTER_RAIN, default=DEFAULT_DELAY_AFTER_RAIN): vol.Coerce(float),
                    vol.Required(CONF_PI_TICK_INTERVAL, default=DEFAULT_PI_TICK_INTERVAL): vol.Coerce(int),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return GreenhouseOptionsFlow()


class GreenhouseOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Greenhouse Controller in 2 steps."""

    def __init__(self):
        self._data = {}

    async def async_step_init(self, user_input=None):
        """Étape 1 des options : Modification des entités."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_parameters()

        options = self.config_entry.options
        data = self.config_entry.data

        def get_val(key):
            return options.get(key, data.get(key))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SENSOR_TEMP_IN, default=get_val(CONF_SENSOR_TEMP_IN)): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Required(CONF_SENSOR_TEMP_OUT, default=get_val(CONF_SENSOR_TEMP_OUT)): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                    vol.Optional(CONF_BINARY_SENSOR_RAIN, default=get_val(CONF_BINARY_SENSOR_RAIN)): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "input_boolean"])
                    ),
                    vol.Optional(CONF_BINARY_SENSOR_WIND, default=get_val(CONF_BINARY_SENSOR_WIND)): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["binary_sensor", "sensor", "input_boolean"])
                    ),
                    vol.Required(CONF_SWITCH_OPEN, default=get_val(CONF_SWITCH_OPEN)): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch", "input_boolean"])
                    ),
                    vol.Required(CONF_SWITCH_CLOSE, default=get_val(CONF_SWITCH_CLOSE)): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["switch", "input_boolean"])
                    ),
                }
            ),
        )

    async def async_step_parameters(self, user_input=None):
        """Étape 2 des options : Modification des paramètres PI."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)

        options = self.config_entry.options
        data = self.config_entry.data

        def get_val(key, default):
            return options.get(key, data.get(key, default))

        return self.async_show_form(
            step_id="parameters",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TEMP_TARGET_MIN, default=get_val(CONF_TEMP_TARGET_MIN, DEFAULT_TEMP_MIN)): vol.Coerce(float),
                    vol.Required(CONF_TEMP_TARGET_MAX, default=get_val(CONF_TEMP_TARGET_MAX, DEFAULT_TEMP_MAX)): vol.Coerce(float),
                    vol.Required(CONF_KP, default=get_val(CONF_KP, DEFAULT_KP)): vol.Coerce(float),
                    vol.Required(CONF_KI, default=get_val(CONF_KI, DEFAULT_KI)): vol.Coerce(float),
                    vol.Required(CONF_INTEGRAL_MAX, default=get_val(CONF_INTEGRAL_MAX, DEFAULT_INTEGRAL_MAX)): vol.Coerce(float),
                    vol.Required(CONF_STEP_SIZE, default=get_val(CONF_STEP_SIZE, DEFAULT_STEP_SIZE)): vol.Coerce(int),
                    vol.Required(CONF_TIME_MAX_OPEN, default=get_val(CONF_TIME_MAX_OPEN, DEFAULT_TIME_MAX_OPEN)): vol.Coerce(float),
                    vol.Required(CONF_TIME_OVERLOAD, default=get_val(CONF_TIME_OVERLOAD, DEFAULT_TIME_OVERLOAD)): vol.Coerce(float),
                    vol.Required(CONF_MAX_VENT, default=get_val(CONF_MAX_VENT, DEFAULT_MAX_VENT)): vol.Coerce(int),
                    vol.Required(CONF_MAX_PLUIE, default=get_val(CONF_MAX_PLUIE, DEFAULT_MAX_PLUIE)): vol.Coerce(int),
                    vol.Required(CONF_DELAY_AFTER_WIND, default=get_val(CONF_DELAY_AFTER_WIND, DEFAULT_DELAY_AFTER_WIND)): vol.Coerce(float),
                    vol.Required(CONF_DELAY_AFTER_RAIN, default=get_val(CONF_DELAY_AFTER_RAIN, DEFAULT_DELAY_AFTER_RAIN)): vol.Coerce(float),
                    vol.Required(CONF_PI_TICK_INTERVAL, default=get_val(CONF_PI_TICK_INTERVAL, DEFAULT_PI_TICK_INTERVAL)): vol.Coerce(int),
                }
            ),
        )