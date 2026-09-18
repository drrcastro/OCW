"""Select entities for choosing an existing vehicle timer."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN


class CarTimerSelect(CoordinatorEntity, SelectEntity):
    """Select an existing timer by its API id and display name."""

    def __init__(self, entry_id: str, car: dict, coordinator=None) -> None:
        if coordinator is not None:
            CoordinatorEntity.__init__(self, coordinator)
        self._entry_id = entry_id
        self._vin = car.get("vin")
        self._car = car
        self._timers: list[dict[str, Any]] = []
        self._attr_current_option = None
        self._attr_icon = "mdi:calendar-edit"

    @property
    def name(self) -> str:
        return f"{self._car.get('nickname') or self._car.get('model_name') or self._vin} Timer"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_timer_select_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("nickname") or self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    @property
    def options(self) -> list[str]:
        return [self._option_for(timer) for timer in self._timers if timer.get("id") is not None]

    @staticmethod
    def _option_for(timer: dict[str, Any]) -> str:
        return f"{timer.get('name') or 'Unnamed timer'} (ID {timer['id']})"

    @property
    def current_option(self) -> str | None:
        return self._attr_current_option if self._attr_current_option in self.options else None

    async def async_select_option(self, option: str) -> None:
        if option in self.options:
            self._attr_current_option = option
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        if self.coordinator:
            self.async_on_remove(
                self.coordinator.async_add_listener(self._handle_coordinator_update)
            )

    def _handle_coordinator_update(self) -> None:
        self.hass.async_create_task(self._async_refresh_from_coordinator())

    async def _async_refresh_from_coordinator(self) -> None:
        await self.async_update()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "vin": self._vin,
            "timers": self._timers,
            "timer_names": {
                self._option_for(timer): timer["id"]
                for timer in self._timers
                if timer.get("id") is not None
            },
        }

    async def async_update(self) -> None:
        client = self.hass.data[DOMAIN][self._entry_id]["client"]
        try:
            timers = await client.async_list_timers(self._vin)
        except Exception:
            return
        self._timers = [timer for timer in timers if isinstance(timer, dict)]
        if self._attr_current_option not in self.options:
            self._attr_current_option = self.options[0] if self.options else None


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")
    cars = coordinator.data if coordinator and coordinator.data is not None else data.get("cars", [])
    entities = [CarTimerSelect(entry.entry_id, car, coordinator) for car in cars if car.get("vin")]
    for entity in entities:
        entity.hass = hass
        await entity.async_update()
    async_add_entities(entities)