"""Platform for switch integration (Greenhouse Controller switches)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .cover import GreenhouseCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Greenhouse switches."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        GreenhouseManualModeSwitch(coordinator),
        GreenhouseRegulationSwitch(coordinator),
    ])


class GreenhouseManualModeSwitch(SwitchEntity):
    """Interrupteur pour activer/désactiver le mode manuel de la serre."""

    def __init__(self, coordinator: GreenhouseCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_name = "Greenhouse Mode Manuel"
        self._attr_unique_id = f"{coordinator._entry.entry_id}_manual_mode"
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
    def is_on(self) -> bool:
        return self.coordinator.is_manual

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.is_manual = True
        await self.coordinator.async_run_regulation()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.is_manual = False
        await self.coordinator.async_run_regulation()

    @property
    def icon(self) -> str:
        return "mdi:hand-back-right" if self.is_on else "mdi:robot"


class GreenhouseRegulationSwitch(SwitchEntity):
    """Interrupteur pour activer/désactiver le calcul sur changement de température."""

    def __init__(self, coordinator: GreenhouseCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_name = "Greenhouse Regulation on Change"
        self._attr_unique_id = f"{coordinator._entry.entry_id}_enable_regulation"
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
    def is_on(self) -> bool:
        return self.coordinator.enable_regulation_on_change

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.enable_regulation_on_change = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.enable_regulation_on_change = False
        self.async_write_ha_state()

    @property
    def icon(self) -> str:
        return "mdi:toggle-switch" if self.is_on else "mdi:toggle-switch-off-outline"