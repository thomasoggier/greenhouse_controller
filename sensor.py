"""Platform for sensor integration (Greenhouse Feedback Sensors)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_SENSOR_TEMP_IN,
    CONF_SENSOR_TEMP_OUT,
    CONF_BINARY_SENSOR_RAIN,
    CONF_BINARY_SENSOR_WIND,
)
from .cover import GreenhouseCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Greenhouse feedback sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        GreenhouseTargetSensor(coordinator),
        GreenhouseTargetPreciseSensor(coordinator),
        GreenhouseStatusSensor(coordinator),
        GreenhouseMovementSensor(coordinator),
        GreenhouseTempInSensor(coordinator),
        GreenhouseTempOutSensor(coordinator),
        GreenhouseRainSensor(coordinator),
        GreenhouseWindSensor(coordinator),
    ])


class GreenhouseBaseSensor(SensorEntity):
    """Base sensor class for greenhouse feedback."""

    def __init__(self, coordinator: GreenhouseCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator._entry.entry_id)},
            "name": "Greenhouse Controller",
            "manufacturer": "Custom",
            "model": "Greenhouse PI Controller",
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.coordinator.register_listener(self.async_write_ha_state)


class GreenhouseTargetSensor(GreenhouseBaseSensor):
    """Capteur pour la position cible finale entière."""

    @property
    def name(self) -> str:
        return "Greenhouse Target Position"

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator._entry.entry_id}_target"

    @property
    def native_value(self) -> int | None:
        if self.coordinator.target_position is None:
            return None
        return int(self.coordinator.target_position)

    @property
    def native_unit_of_measurement(self) -> str:
        return "%"


class GreenhouseTargetPreciseSensor(GreenhouseBaseSensor):
    """Capteur pour la valeur précise calculée par le régulateur PI."""

    @property
    def name(self) -> str:
        return "Greenhouse Target Precise"

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator._entry.entry_id}_target_precis"

    @property
    def native_value(self) -> float:
        return round(self.coordinator.output_pi_precise, 2)

    @property
    def native_unit_of_measurement(self) -> str:
        return "%"


class GreenhouseStatusSensor(GreenhouseBaseSensor):
    """Capteur du mode actuel (Normal, Manuel, Alarme Vent, Alarme Pluie)."""

    @property
    def name(self) -> str:
        return "Greenhouse Status Mode"

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator._entry.entry_id}_status"

    @property
    def native_value(self) -> str:
        mapping = {
            "normal": "Normal",
            "manual": "Manuel",
            "wind_alarm": "Alarme Vent",
            "rain_alarm": "Alarme Pluie",
        }
        return mapping.get(self.coordinator.status_mode, self.coordinator.status_mode)

    @property
    def icon(self) -> str:
        if self.coordinator.status_mode == "manual":
            return "mdi:hand-back-right"
        elif "alarm" in self.coordinator.status_mode:
            return "mdi:alert"
        return "mdi:check-circle"


class GreenhouseMovementSensor(GreenhouseBaseSensor):
    """Capteur de mouvement (Ouverture, Fermeture, Ne bouge pas)."""

    @property
    def name(self) -> str:
        return "Greenhouse Movement State"

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator._entry.entry_id}_movement"

    @property
    def native_value(self) -> str:
        if self.coordinator.is_opening:
            return "En train de s'ouvrir"
        elif self.coordinator.is_closing:
            return "En train de se fermer"
        return "Ne bouge pas"

    @property
    def icon(self) -> str:
        if self.coordinator.is_opening:
            return "mdi:arrow-up-box"
        elif self.coordinator.is_closing:
            return "mdi:arrow-down-box"
        return "mdi:stop-circle-outline"


class GreenhouseTempInSensor(GreenhouseBaseSensor):
    """Capteur reflétant la température intérieure lue par l'intégration."""

    @property
    def name(self) -> str:
        return "Greenhouse Temp In"

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator._entry.entry_id}_temp_in"

    @property
    def native_value(self) -> float:
        cfg = self.coordinator.cfg
        state = self.coordinator.hass.states.get(cfg.get(CONF_SENSOR_TEMP_IN))
        try:
            return float(state.state) if state and state.state not in ("unavailable", "unknown") else 0.0
        except ValueError:
            return 0.0

    @property
    def native_unit_of_measurement(self) -> str:
        return "°C"


class GreenhouseTempOutSensor(GreenhouseBaseSensor):
    """Capteur reflétant la température extérieure lue par l'intégration."""

    @property
    def name(self) -> str:
        return "Greenhouse Temp Out"

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator._entry.entry_id}_temp_out"

    @property
    def native_value(self) -> float:
        cfg = self.coordinator.cfg
        state = self.coordinator.hass.states.get(cfg.get(CONF_SENSOR_TEMP_OUT))
        try:
            return float(state.state) if state and state.state not in ("unavailable", "unknown") else 0.0
        except ValueError:
            return 0.0

    @property
    def native_unit_of_measurement(self) -> str:
        return "°C"


class GreenhouseRainSensor(GreenhouseBaseSensor):
    """Capteur d'état de la pluie (incluant le délai post-pluie)."""

    @property
    def name(self) -> str:
        return "Greenhouse Rain Status"

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator._entry.entry_id}_rain_status"

    @property
    def native_value(self) -> str:
        return "En cours / Temporisation" if self.coordinator.status_mode == "rain_alarm" else "Sec / Normal"

    @property
    def icon(self) -> str:
        return "mdi:weather-pouring" if self.coordinator.status_mode == "rain_alarm" else "mdi:weather-sunny"


class GreenhouseWindSensor(GreenhouseBaseSensor):
    """Capteur d'état du vent (incluant le délai post-vent)."""

    @property
    def name(self) -> str:
        return "Greenhouse Wind Status"

    @property
    def unique_id(self) -> str:
        return f"{self.coordinator._entry.entry_id}_wind_status"

    @property
    def native_value(self) -> str:
        return "En cours / Temporisation" if self.coordinator.status_mode == "wind_alarm" else "Calme / Normal"

    @property
    def icon(self) -> str:
        return "mdi:weather-windy" if self.coordinator.status_mode == "wind_alarm" else "mdi:weather-windy-variant"