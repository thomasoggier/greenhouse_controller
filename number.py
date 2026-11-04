"""Platform for number integration (Greenhouse Parameters & Manual Position)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_TEMP_TARGET_MIN,
    CONF_TEMP_TARGET_MAX,
    CONF_PI_TICK_INTERVAL,
    CONF_KP,
    CONF_KI,
    CONF_INTEGRAL_MAX,
    CONF_STEP_SIZE,
    CONF_TIME_MAX_OPEN,
    CONF_TIME_OVERLOAD,
    CONF_MAX_VENT,
    CONF_MAX_PLUIE,
    CONF_DELAY_AFTER_WIND,
    CONF_DELAY_AFTER_RAIN,
)
from .cover import GreenhouseCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Greenhouse parameter numbers and manual position."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    numbers = [
        # Curseur de position manuelle natif
        GreenhouseManualPositionEntity(coordinator),
        # Paramètres de régulation
        GreenhouseNumberEntity(coordinator, CONF_TEMP_TARGET_MIN, "Target Temp Min", "°C", 0, 50, 0.5),
        GreenhouseNumberEntity(coordinator, CONF_TEMP_TARGET_MAX, "Target Temp Max", "°C", 10, 60, 0.5),
        GreenhouseNumberEntity(coordinator, CONF_PI_TICK_INTERVAL, "PI Tick Interval", "s", 10, 300, 5),
        GreenhouseNumberEntity(coordinator, CONF_KP, "Gain Kp", None, 0, 50, 0.1),
        GreenhouseNumberEntity(coordinator, CONF_KI, "Gain Ki", None, 0, 5, 0.01),
        GreenhouseNumberEntity(coordinator, CONF_INTEGRAL_MAX, "Integral Max", None, 0, 2000, 10),
        GreenhouseNumberEntity(coordinator, CONF_STEP_SIZE, "Step Size", "%", 1, 100, 1),
        GreenhouseNumberEntity(coordinator, CONF_TIME_MAX_OPEN, "Time Max Open", "s", 5, 300, 1),
        GreenhouseNumberEntity(coordinator, CONF_TIME_OVERLOAD, "Time Overload", "s", 0, 30, 1),
        GreenhouseNumberEntity(coordinator, CONF_MAX_VENT, "Max Open Wind", "%", 0, 100, 1),
        GreenhouseNumberEntity(coordinator, CONF_MAX_PLUIE, "Max Open Rain", "%", 0, 100, 1),
        GreenhouseNumberEntity(coordinator, CONF_DELAY_AFTER_WIND, "Delay After Wind", "min", 0, 180, 1),
        GreenhouseNumberEntity(coordinator, CONF_DELAY_AFTER_RAIN, "Delay After Rain", "min", 0, 180, 1),
    ]
    
    async_add_entities(numbers)


class GreenhouseManualPositionEntity(NumberEntity):
    """Curseur natif pour définir la position manuelle de la serre."""

    def __init__(self, coordinator: GreenhouseCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_name = "Greenhouse Manual Position"
        self._attr_unique_id = f"{coordinator._entry.entry_id}_manual_position"
        self._attr_native_unit_of_measurement = "%"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator._entry.entry_id)},
            "name": "Greenhouse Controller",
            "manufacturer": "Custom",
            "model": "Greenhouse PI Controller",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.coordinator.register_listener(self.async_write_ha_state)

    @property
    def native_value(self) -> float:
        return float(self.coordinator.manual_position)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.manual_position = int(value)
        self.async_write_ha_state()
        await self.coordinator.async_run_regulation()


class GreenhouseNumberEntity(NumberEntity):
    """Représentation d'un paramètre réglable sous forme de nombre."""

    def __init__(
        self,
        coordinator: GreenhouseCoordinator,
        key: str,
        name_suffix: str,
        unit: str | None,
        min_val: float,
        max_val: float,
        step: float,
    ) -> None:
        self.coordinator = coordinator
        self._key = key
        self._attr_name = f"Greenhouse {name_suffix}"
        self._attr_unique_id = f"{coordinator._entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_mode = NumberMode.BOX
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator._entry.entry_id)},
            "name": "Greenhouse Controller",
            "manufacturer": "Custom",
            "model": "Greenhouse PI Controller",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.coordinator.register_listener(self.async_write_ha_state)

    @property
    def native_value(self) -> float:
        cfg = self.coordinator.cfg
        return float(cfg.get(self._key, self._attr_native_min_value))

    async def async_set_native_value(self, value: float) -> None:
        entry = self.coordinator._entry
        new_options = {**entry.options, self._key: value}
        self.hass.config_entries.async_update_entry(entry, options=new_options)
        await self.coordinator.async_run_regulation()
        self.async_write_ha_state()