"""Switch platform to control car climate (A/C) as a simple switch."""
from __future__ import annotations

from typing import Any
import asyncio
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

AC_CONFIRMATION_INTERVAL = 5
AC_CONFIRMATION_ATTEMPTS = 6


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


class CarACSwitch(CoordinatorEntity, SwitchEntity):
    """Represents the car A/C as a switch."""

    def __init__(self, entry_id: str, car: dict, coordinator=None) -> None:
        if coordinator is not None:
            CoordinatorEntity.__init__(self, coordinator)
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._coordinator = coordinator

    @property
    def name(self) -> str:
        return f"{self._car.get('model_name') or 'Car'} A/C"

    @property
    def unique_id(self) -> str:
        return f"ocw_integration_ac_{self._vin}"

    @property
    def is_on(self) -> bool | None:
        """Return the actual A/C state reported by the latest car update."""
        car = self._get_car()
        ev_info = car.get("ev_info") or {}
        value = ev_info.get("ac_status") if isinstance(ev_info, dict) else None
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"0", "false", "off", "no", "inactive"}:
                return False
            if normalized in {"1", "true", "on", "yes", "active"}:
                return True
        return bool(value)

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
        """Poll until the car reports the requested A/C state or times out."""
        if not self._coordinator:
            return

        for attempt in range(AC_CONFIRMATION_ATTEMPTS):
            await self._coordinator.async_request_refresh()
            actual = self.is_on
            if actual == expected:
                return

            if attempt < AC_CONFIRMATION_ATTEMPTS - 1:
                await asyncio.sleep(AC_CONFIRMATION_INTERVAL)

        _LOGGER.warning(
            "OpenCARWINGS did not confirm A/C=%s for %s after %s attempts (reported=%s)",
            expected,
            self._vin,
            AC_CONFIRMATION_ATTEMPTS,
            self.is_on,
        )


def hass_client(hass, entry_id: str):
    """Helper to get the API client stored in hass.data."""
    return hass.data[DOMAIN][entry_id]["client"]
