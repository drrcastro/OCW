"""Switch platform to control car climate (A/C) as a simple switch."""
from __future__ import annotations

from typing import Any
import logging

from homeassistant.components.switch import SwitchEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    cars = data.get("cars", [])

    entities = []
    for car in cars:
        if car.get("vin"):
            ent = CarACSwitch(entry.entry_id, car, coordinator=data.get("coordinator"))
            # Tests call entity methods directly; set hass here for testability
            ent.hass = hass
            entities.append(ent)

    async_add_entities(entities)


class CarACSwitch(SwitchEntity):
    """Represents the car A/C as a switch."""

    def __init__(self, entry_id: str, car: dict, coordinator=None) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._coordinator = coordinator

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} A/C"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_ac_{self._vin}"

    @property
    def is_on(self) -> bool | None:
        """Return the actual A/C state reported by the latest car update."""
        car = self._get_car()
        ev_info = car.get("ev_info") or {}
        value = ev_info.get("ac_status") if isinstance(ev_info, dict) else None
        return bool(value) if value is not None else None

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_turn_on(self, **kwargs) -> None:
        """Turn A/C on by sending command_type 3 to `/api/command/{vin}/`."""
        if self.is_on is True:
            return
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_send_command(self._vin, 3)  # 3 = A/C on
            await self._refresh_and_verify(True)
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to turn A/C on for %s", self._vin)
            raise

    async def async_turn_off(self, **kwargs) -> None:
        """Turn A/C off by sending command_type 4."""
        if self.is_on is False:
            return
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_send_command(self._vin, 4)  # 4 = A/C off
            await self._refresh_and_verify(False)
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to turn A/C off for %s", self._vin)
            raise

    def _get_car(self) -> dict:
        if self._coordinator and getattr(self._coordinator, "data", None):
            for car in self._coordinator.data:
                if car.get("vin") == self._vin:
                    return {**self._car, **car}
        return self._car

    async def _refresh_and_verify(self, expected: bool) -> None:
        """Refresh state after a command and report if the car did not confirm it."""
        if not self._coordinator:
            return
        await self._coordinator.async_request_refresh()
        actual = self.is_on
        if actual is not None and actual != expected:
            _LOGGER.warning(
                "OpenCARWINGS did not confirm A/C=%s for %s (reported=%s)",
                expected,
                self._vin,
                actual,
            )


def hass_client(hass, entry_id: str):
    """Helper to get the API client stored in hass.data."""
    return hass.data[DOMAIN][entry_id]["client"]
