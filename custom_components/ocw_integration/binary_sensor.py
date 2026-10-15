"""Binary sensors for OpenCARWINGS vehicle charging state."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN


class CarEVInfoBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Represent a boolean value from a car's EV information."""

    def __init__(
        self,
        entry_id: str,
        car: dict[str, Any],
        key: str,
        name: str,
        device_class: BinarySensorDeviceClass,
        coordinator=None,
    ) -> None:
        if coordinator is not None:
            CoordinatorEntity.__init__(self, coordinator)
        self._car = car
        self._vin = car["vin"]
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"ocw_integration_{key}_{self._vin}"
        self._attr_device_class = device_class

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("nickname") or self._car.get("model_name") or "Car",
            "manufacturer": self._car.get("make") or "Nissan",
            "model": self._car.get("model_name") or "Leaf",
        }

    @property
    def is_on(self) -> bool | None:
        car = self._car
        coordinator = getattr(self, "coordinator", None)
        if coordinator and getattr(coordinator, "data", None):
            for updated_car in coordinator.data:
                if updated_car.get("vin") == self._vin:
                    car = {**self._car, **updated_car}
                    break

        ev_info = car.get("ev_info")
        if not isinstance(ev_info, dict):
            return None

        value = ev_info.get(self._key)
        if isinstance(value, bool):
            return value
        if value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "on", "yes", "1"}:
                return True
            if normalized in {"false", "off", "no", "0"}:
                return False
        return None


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    """Set up per-car EV state binary sensors."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")
    cars = (
        coordinator.data
        if coordinator and coordinator.data is not None
        else data.get("cars", [])
    )

    entities: list[CarEVInfoBinarySensor] = []
    for car in cars:
        if not car.get("vin"):
            continue
        entities.extend(
            (
                CarEVInfoBinarySensor(
                    entry.entry_id,
                    car,
                    "power_available",
                    "Power Available",
                    BinarySensorDeviceClass.POWER,
                    coordinator,
                ),
                CarEVInfoBinarySensor(
                    entry.entry_id,
                    car,
                    "charging_interrupted",
                    "Charging Interrupted",
                    BinarySensorDeviceClass.PROBLEM,
                    coordinator,
                ),
            )
        )

    async_add_entities(entities)
