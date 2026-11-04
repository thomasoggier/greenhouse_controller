"""Platform for number integration (Greenhouse Controller parameters & manual position)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
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

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Greenhouse parameter numbers and manual position."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    numbers = [
        GreenhouseManualPositionEntity(coordinator),
        GreenhouseNumberEntity(coordinator, CONF_TEMP_TARGET_MIN, "Target Temp Min", "°C", 0, 50, 0.5),
        GreenhouseNumberEntity(coordinator, CONF_TEMP_TARGET_MAX, "Target Temp Max", "°C", 10, 60, 0.5),
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
        GreenhouseNumberEntity(coordinator, CONF_PI_TICK_INTERVAL, "PI Tick Interval", "s", 10, 300, 5),
    ]
    
    async_add_entities(numbers)


class GreenhouseManualPositionEntity(NumberEntity, RestoreEntity):
    """Entité number pour piloter et restaurer la position manuelle souhaitée."""

    def __init__(self, coordinator) -> None:
        self.coordinator = coordinator
        self._attr_name = "Greenhouse Manual Position"
        self._attr_unique_id = f"{coordinator._entry.entry_id}_manual_position"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "%"
        self._attr_mode = NumberMode.SLIDER
        self._attr_icon = "mdi:tune"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator._entry.entry_id)},
            "name": "Greenhouse Controller",
            "manufacturer": "Custom",
            "model": "Greenhouse PI Controller",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.coordinator.register_listener(self.async_write_ha_state)

        # Restauration de la dernière valeur du curseur manuel avant redémarrage
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                val = float(last_state.state)
                self.coordinator.manual_position = int(val)
            except ValueError:
                pass

    @property
    def native_value(self) -> float:
        return float(self.coordinator.manual_position)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.manual_position = int(value)
        self.async_write_ha_state()
        # Si le mode manuel est actif, le mouvement s'exécute immédiatement
        if self.coordinator.is_manual:
            await self.coordinator.async_run_regulation()


class GreenhouseNumberEntity(NumberEntity, RestoreEntity):
    """Entité number générique pour les paramètres de configuration de la serre (avec restauration)."""

    def __init__(self, coordinator, key: str, name: str, unit: str | None, min_v: float, max_v: float, step_v: float) -> None:
        self.coordinator = coordinator
        self._key = key
        self._attr_name = f"Greenhouse {name}"
        self._attr_unique_id = f"{coordinator._entry.entry_id}_{key}"
        self._attr_native_min_value = min_v
        self._attr_native_max_value = max_v
        self._attr_native_step = step_v
        self._attr_native_unit_of_measurement = unit
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

        # Restauration éventuelle de la valeur du paramètre si modifiée dynamiquement
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                val = float(last_state.state)
                # On met à jour les options en mémoire du coordinateur
                if self._key not in self.coordinator._entry.options:
                    options = dict(self.coordinator._entry.options)
                    options[self._key] = val
                    self.coordinator.hass.config_entries.async_update_entry(
                        self.coordinator._entry, options=options
                    )
            except ValueError:
                pass

    @property
    def native_value(self) -> float:
        cfg = self.coordinator.cfg
        # Valeur par défaut de secours si besoin
        return float(cfg.get(self._key, 0))

    async def async_set_native_value(self, value: float) -> None:
        options = dict(self.coordinator._entry.options)
        options[self._key] = value
        self.coordinator.hass.config_entries.async_update_entry(
            self.coordinator._entry, options=options
        )
        self.async_write_ha_state()