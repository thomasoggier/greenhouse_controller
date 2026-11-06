"""Platform for cover integration (Greenhouse Vantaux Controller)."""
from __future__ import annotations
import asyncio
from datetime import timedelta
import logging
import time

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

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

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Greenhouse cover platform from a config entry."""
    coordinator = GreenhouseCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator
    async_add_entities([GreenhouseCoverEntity(coordinator)])


class GreenhouseCoordinator:
    """Coordinateur centralisant la régulation PI (avec dt temporel), le mode manuel et les états."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        
        self.position = 0
        self.target_position = None
        self.output_pi_precise = 0.0
        self.is_opening = False
        self.is_closing = False
        self.status_mode = "start"
        
        # États manuels et interrupteur gérés en interne
        self.is_manual = False
        self.manual_position = 0
        self.enable_regulation_on_change = True
        
        self._rain_clear_time = 0.0
        self._wind_clear_time = 0.0
        self._integral = 0.0
        self._last_time = 0.0
        self._initialized = False
        self._move_task: asyncio.Task | None = None
        self._listeners = []

    @property
    def cfg(self):
        return {**self._entry.data, **self._entry.options}

    def register_listener(self, cb):
        self._listeners.append(cb)

    def notify_listeners(self):
        for cb in self._listeners:
            cb()

    def restore_previous_state(self, entity_id: str) -> None:
        """Récupère la dernière position enregistrée de l'entité cover dans Home Assistant."""
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unavailable", "unknown", None):
            try:
                pos = state.attributes.get("current_position")
                if pos is not None:
                    self.position = int(pos)
                    self.target_position = int(pos)
                    return
                if state.state == "closed":
                    self.position = 0
                    self.target_position = 0
                    return
            except ValueError:
                pass
        
        # Si aucun état valide n'est trouvé au démarrage, on force une position par défaut sécurisée 
        # (par exemple 0 fermé ou on bloque la régulation automatique tant qu'un statut manuel/explicite n'est pas donné)
        if self.position is None:
            _LOGGER.warning("Greenhouse Position | Impossible de restaurer l'état précédent. Position initialisée par sécurité à 0% (fermée).")
            self.position = 0
            self.target_position = 0

    async def async_run_regulation(self) -> None:
        # Sécurité : Si la serre est déjà en mouvement, on ignore ce cycle
        if self.is_opening or self.is_closing:
            return

        cfg = self.cfg
        now = time.time()

        # 1. Mode Manuel Natif
        if self.is_manual:
            self.status_mode = "manual"
            self._last_time = now
            self._initialized = False
            self.notify_listeners()
            if self.manual_position != self.target_position or self.manual_position in (0, 100):
                await self._move_to(self.manual_position)
            return      

        # 2. Lecture sécurisée des capteurs de température
        temp_in_state = self.hass.states.get(cfg.get(CONF_SENSOR_TEMP_IN))
        temp_out_state = self.hass.states.get(cfg.get(CONF_SENSOR_TEMP_OUT))

        if not temp_in_state or temp_in_state.state in ("unavailable", "unknown"):
            return
        if not temp_out_state or temp_out_state.state in ("unavailable", "unknown"):
            return

        try:
            temp_in = float(temp_in_state.state)
            temp_out = float(temp_out_state.state)
        except ValueError:
            return

        # Initialisation propre du dt au premier vrai passage avec des données valides
        if not self._initialized:
            self._last_time = now
            self._initialized = True
            self._integral = 0.0

        rain_state = self.hass.states.get(cfg.get(CONF_BINARY_SENSOR_RAIN)) if cfg.get(CONF_BINARY_SENSOR_RAIN) else None
        wind_state = self.hass.states.get(cfg.get(CONF_BINARY_SENSOR_WIND)) if cfg.get(CONF_BINARY_SENSOR_WIND) else None

        is_raining_raw = rain_state.state in ("on", "true", "True", "1", "rain", "wet") if rain_state else False
        is_windy_raw = wind_state.state in ("on", "true", "True", "1", "wind", "storm") if wind_state else False

        delay_rain_sec = cfg.get(CONF_DELAY_AFTER_RAIN, DEFAULT_DELAY_AFTER_RAIN) * 60.0
        delay_wind_sec = cfg.get(CONF_DELAY_AFTER_WIND, DEFAULT_DELAY_AFTER_WIND) * 60.0

        if is_raining_raw:
            self._rain_clear_time = now + delay_rain_sec
        if is_windy_raw:
            self._wind_clear_time = now + delay_wind_sec

        alarm_pluie = is_raining_raw or (now < self._rain_clear_time)
        alarm_vent = is_windy_raw or (now < self._wind_clear_time)

        if alarm_vent:
            self.status_mode = "wind_alarm"
        elif alarm_pluie:
            self.status_mode = "rain_alarm"
        else:
            self.status_mode = "normal"

        t_min = cfg.get(CONF_TEMP_TARGET_MIN, DEFAULT_TEMP_MIN)
        t_max = cfg.get(CONF_TEMP_TARGET_MAX, DEFAULT_TEMP_MAX)
        kp = cfg.get(CONF_KP, DEFAULT_KP)
        ki = cfg.get(CONF_KI, DEFAULT_KI)
        integral_max = cfg.get(CONF_INTEGRAL_MAX, DEFAULT_INTEGRAL_MAX)
        step = cfg.get(CONF_STEP_SIZE, DEFAULT_STEP_SIZE)
        max_vent = cfg.get(CONF_MAX_VENT, DEFAULT_MAX_VENT)
        max_pluie = cfg.get(CONF_MAX_PLUIE, DEFAULT_MAX_PLUIE)

        # 3. Calcul rigoureux du dt temporel pour le PI
        dt = (now - self._last_time)
        self._last_time = now
        if dt <= 0 or dt > 600:
            dt = cfg.get(CONF_PI_TICK_INTERVAL, DEFAULT_PI_TICK_INTERVAL)

        output_pi = 0.0
        if temp_in <= t_min:
            output_pi = 0.0
            self._integral = 0.0
        elif temp_in >= t_max:
            output_pi = 100.0
        else:
            plage_total = t_max - t_min
            pos_prop = ((temp_in - t_min) / plage_total) * 100.0
            error = temp_in - (t_min + t_max) / 2.0

            # Intégration anti-windup basée sur le véritable dt temporel
            if error > 0.5:
                self._integral += error * dt
            elif error < -0.1:
                self._integral = 0.0
            self._integral = max(0.0, min(self._integral, integral_max))

            output_pi = pos_prop + (ki * self._integral)
            output_pi = max(0.0, min(100.0, output_pi))

        # 4. Feed-forward (correction air extérieur)
        delta_t = max(temp_in - temp_out, 1.0)
        facteur_air = 15.0 / delta_t
        if t_min < temp_in < t_max:
            output_pi = output_pi * max(0.4, min(1.5, facteur_air))

        self.output_pi_precise = output_pi

        # 5. Arrondi par pas
        ouverture_finale = round(output_pi / step) * step
        if temp_in >= t_max:
            ouverture_finale = 100
        if temp_in <= t_min:
            ouverture_finale = 0

        # 6. Sécurités Vent / Pluie (Prioritaires et immédiates)
        if alarm_vent:
            ouverture_finale = min(ouverture_finale, max_vent)
        if alarm_pluie:
            ouverture_finale = min(ouverture_finale, max_pluie)

        ouverture_finale = max(0, min(100, ouverture_finale))
# Journalisation détaillée du calcul PI pour le débogage
        _LOGGER.debug(
            "Greenhouse Calc | T_in: %.1f°C | T_out: %.1f°C | T_target min-max [%.1f - %.1f] | "
            "dt: %.1f sec | Erreur: %.2f | Prop: %.1f%% | Intégrale: %.2f | "
            "PI Précis: %.1f%% | Arrondi/Pas: %d%% | Pluie: %s (alarm: %s) | Vent: %s (alarm: %s) | Mode: %s",
            temp_in,
            temp_out,
            t_min,
            t_max,
            dt,
            error if 'error' in locals() else 0.0,
            pos_prop if 'pos_prop' in locals() else 0.0,
            self._integral,
            output_pi,
            ouverture_finale,
            is_raining_raw,
            alarm_pluie,
            is_windy_raw,
            alarm_vent,
            self.status_mode,
        )
        self.notify_listeners()
        if ouverture_finale != self.target_position or ouverture_finale == 0 or ouverture_finale == 100:
            await self._move_to(ouverture_finale)

    async def _move_to(self, target_position: int) -> None:
        if self.position is None:
            _LOGGER.error("Greenhouse Move | Position actuelle inconnue. Impossible de calculer le déplacement.")
            return
        if self._move_task and not self._move_task.done():
            self._move_task.cancel()

        self.target_position = target_position
        diff = target_position - self.position

        if diff == 0:
            self.is_opening = False
            self.is_closing = False
            self.notify_listeners()
            return

        cfg = self.cfg
        time_max = cfg.get(CONF_TIME_MAX_OPEN, DEFAULT_TIME_MAX_OPEN)
        overload = cfg.get(CONF_TIME_OVERLOAD, DEFAULT_TIME_OVERLOAD)

        if target_position in (0, 100):
            duration = time_max + overload
        else:
            duration = (abs(diff) / 100.0) * time_max

        direction = "open" if diff > 0 else "close"
        self.is_opening = (direction == "open")
        self.is_closing = (direction == "close")
        self.notify_listeners()
        # Journalisation détaillée des mouvements
        _LOGGER.debug(
            "Greenhouse Move | Position actuelle: %d%% -> Position cible: %d%% | "
            "Delta: %d%% | Direction: %s | Durée prévue: %.1fs (dont overload: %.1fs)",
            self.position,
            target_position,
            diff,
            direction,
            duration,
            overload if target_position in (0, 100) else 0.0,
        )
        await self._activate_relay(direction)

        self._move_task = self.hass.async_create_task(
            self._async_stop_after_delay(duration, target_position)
        )

    async def _async_stop_after_delay(self, duration: float, target_position: int) -> None:
        # Journalisation de l'arrivée à destination
        _LOGGER.debug(
            "Greenhouse Move Finished | Vantaux arrêtés à la position: %d%%",
            target_position
        )
        try:
            await asyncio.sleep(duration)
            await self._turn_relays_off()
            self.position = target_position
            self.is_opening = False
            self.is_closing = False
            self.notify_listeners()
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        if self._move_task and not self._move_task.done():
            self._move_task.cancel()
        await self._turn_relays_off()
        self.is_opening = False
        self.is_closing = False
        self.notify_listeners()

    async def _activate_relay(self, direction: str) -> None:
        cfg = self.cfg
        switch_open = cfg.get(CONF_SWITCH_OPEN)
        switch_close = cfg.get(CONF_SWITCH_CLOSE)

        if direction == "open":
            await self.hass.services.async_call("homeassistant", "turn_on", {"entity_id": switch_open})
            await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": switch_close})
        else:
            await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": switch_open})
            await self.hass.services.async_call("homeassistant", "turn_on", {"entity_id": switch_close})

    async def _turn_relays_off(self) -> None:
        cfg = self.cfg
        switch_open = cfg.get(CONF_SWITCH_OPEN)
        switch_close = cfg.get(CONF_SWITCH_CLOSE)

        if switch_open:
            await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": switch_open})
        if switch_close:
            await self.hass.services.async_call("homeassistant", "turn_off", {"entity_id": switch_close})


class GreenhouseCoverEntity(CoverEntity):
    """Représentation de la serre en tant qu'entité Cover."""

    def __init__(self, coordinator: GreenhouseCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_name = "Greenhouse Controller"
        self._attr_unique_id = coordinator._entry.entry_id
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.coordinator.register_listener(self.async_write_ha_state)

        # Restauration de la position précédente
        self.coordinator.restore_previous_state(self.entity_id)

        cfg = self.coordinator.cfg
        temp_entities = [
            cfg.get(CONF_SENSOR_TEMP_IN),
            cfg.get(CONF_SENSOR_TEMP_OUT),
        ]
        temp_entities = [e for e in temp_entities if e]

        safety_entities = [
            cfg.get(CONF_BINARY_SENSOR_RAIN),
            cfg.get(CONF_BINARY_SENSOR_WIND),
        ]
        safety_entities = [e for e in safety_entities if e]

        # 1. Écoute des températures (soumises au switch enable_regulation_on_change)
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, temp_entities, self._async_temp_updated
            )
        )

        # 2. Écoute de la pluie et du vent (réaction IMMÉDIATE indépendante du switch)
        if safety_entities:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, safety_entities, self._async_safety_updated
                )
            )

        # 3. Déclenchement périodique basé sur le dt configuré
        tick_interval_sec = cfg.get(CONF_PI_TICK_INTERVAL, DEFAULT_PI_TICK_INTERVAL)
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_timer_tick, timedelta(seconds=tick_interval_sec)
            )
        )

        # Lancement initial au démarrage
        self.hass.async_create_task(self.coordinator.async_run_regulation())

    async def _async_temp_updated(self, event) -> None:
        """Déclenché sur changement de température (si l'interrupteur est actif)."""
        if self.coordinator.enable_regulation_on_change:
            await self.coordinator.async_run_regulation()

    async def _async_safety_updated(self, event) -> None:
        """Déclenché IMMÉDIATEMENT sur changement de pluie ou de vent (prioritaire)."""
        await self.coordinator.async_run_regulation()

    async def _async_timer_tick(self, now) -> None:
        """Appelé selon le dt configuré pour actualiser le terme intégral du PI."""
        await self.coordinator.async_run_regulation()

    @property
    def current_cover_position(self) -> int | None:
        return int(self.coordinator.position)

    @property
    def is_closing(self) -> bool:
        return self.coordinator.is_closing

    @property
    def is_opening(self) -> bool:
        return self.coordinator.is_opening

    @property
    def is_closed(self) -> bool:
        return self.coordinator.position == 0

    async def async_set_cover_position(self, **kwargs) -> None:
        pos = kwargs.get("position")
        if pos is not None:
            await self.coordinator._move_to(pos)

    async def async_open_cover(self, **kwargs) -> None:
        await self.coordinator._move_to(100)

    async def async_close_cover(self, **kwargs) -> None:
        await self.coordinator._move_to(0)

    async def async_stop_cover(self, **kwargs) -> None:
        await self.coordinator.stop()