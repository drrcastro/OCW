"""Sensor platform for OpenCARWINGS listing cars."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION, PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity

try:
    from homeassistant.helpers.entity import EntityCategory
except Exception:  # pragma: no cover
    class EntityCategory:  # type: ignore
        DIAGNOSTIC = "diagnostic"

try:
    from homeassistant.components.sensor import SensorDeviceClass
except Exception:  # pragma: no cover
    class SensorDeviceClass:  # type: ignore
        BATTERY = "battery"

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


# -----------------------------
# Helpers
# -----------------------------

def _parse_ts(value: str | None):
    if not value:
        return None
    try:
        # support ISO8601 like `2026-01-04T12:00:00Z` or with microseconds `...10.419903Z`
        if value.endswith("Z"):
            try:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            except ValueError:
                return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _format_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    try:
        ts = dt.isoformat()
        if ts.endswith("+00:00"):
            ts = ts.replace("+00:00", "Z")
        return ts
    except Exception:
        return None


def _ev_getter(key: str, fallback: str | None = None) -> Callable[[dict], Any]:
    """Get value from car['ev_info'][key], falling back to car[fallback] or car[key]."""
    def _get(car: dict):
        ev = car.get("ev_info") or {}
        if isinstance(ev, dict) and key in ev:
            return ev.get(key)
        if fallback:
            return car.get(fallback)
        return car.get(key)
    return _get


def _health_getter(key: str) -> Callable[[dict], Any]:
    """Get a value from the vehicle health report."""
    def _get(car: dict):
        health = car.get("veh_health") or {}
        return health.get(key) if isinstance(health, dict) else None
    return _get

def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _tpms_bar(v: Any) -> float | None:
    """Convert the API's TPMS centibar value to bar."""
    value = _to_float(v)
    return round(value / 100, 2) if value is not None else None

def _round_1(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return round(float(v), 1)
    except Exception:
        return None


def _to_kwh(v: Any) -> float | None:
    value = _to_float(v)
    return round(value / 1000, 2) if value is not None else None
    try:
        return round(float(v), 1)
    except Exception:
        return None

# -----------------------------
# Base per-car entity
# -----------------------------

class OpenCarwingsCarEntity(CoordinatorEntity):
    """Base entity for a single car identified by VIN.

    - merges seed car dict (from initial cars list) with coordinator car dict
      so fields like odometer don't disappear if coordinator payload is missing them
    """

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: dict | None = None) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._vin = vin
        self._seed_car = seed_car or {}

    def _get_car(self) -> dict:
        # Merge: seed -> coordinator (coordinator wins, seed fills missing fields)
        if self.coordinator and getattr(self.coordinator, "data", None):
            for c in self.coordinator.data:
                if c.get("vin") == self._vin:
                    return {**self._seed_car, **(c or {})}
        return self._seed_car or {}

    @property
    def device_info(self) -> dict[str, Any]:
        car = self._get_car()
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": car.get("nickname") or car.get("model_name") or "Car",
            "manufacturer": car.get("make") or "Nissan",
            "model": car.get("model_name") or "Leaf",
        }



@dataclass(frozen=True)
class CarSensorSpec:
    key: str
    name: str
    value: Callable[[dict], Any]
    transform: Optional[Callable[[Any], Any]] = None
    device_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    icon: Optional[str] = None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _plugged_to_str(v: Any) -> str:
    return "plugged" if bool(v) else "unplugged"


SENSOR_ICONS = {
    "range_acon": "mdi:car-speed-limiter",
    "range_acoff": "mdi:car-speed-limiter",
    "soc": "mdi:battery-medium",
    "soc_display": "mdi:battery-medium",
    "charge_bars": "mdi:battery-charging",
    "plugged_in": "mdi:ev-plug-type2",
    "charging": "mdi:battery-charging",
    "charge_finish": "mdi:battery-check",
    "quick_charging": "mdi:flash",
    "ac_status": "mdi:air-conditioner",
    "eco_mode": "mdi:leaf",
    "car_running": "mdi:engine",
    "odometer": "mdi:counter",
    "full_chg_time": "mdi:timer-sand",
    "limit_chg_time": "mdi:timer-cog",
    "obc_6kw": "mdi:ev-station",
    "car_gear": "mdi:car-shift-pattern",
    "soh": "mdi:battery-heart-variant",
    "wh_content": "mdi:lightning-bolt",
    "cap_bars": "mdi:battery-outline",
    "gids": "mdi:battery-arrow-down",
    "counter": "mdi:counter",
    "max_gids": "mdi:battery-arrow-up",
    "param21": "mdi:tune-variant",
    "cabin_temp": "mdi:car-seat-cooler",
    "force_soc_display": "mdi:format-display",
    "obc_6kw_avail": "mdi:ev-station",
    "batt_heater_avail": "mdi:radiator",
    "batt_heater_status": "mdi:radiator",
    "signal_level": "mdi:signal-cellular-3",
    "tpms_fl": "mdi:tire",
    "tpms_fr": "mdi:tire",
    "tpms_rl": "mdi:tire",
    "tpms_rr": "mdi:tire",
    "tpms_light": "mdi:tire-alert",
    "maintenance_alert": "mdi:car-wrench",
    "health_mileage": "mdi:clipboard-pulse",
}


CAR_SENSORS: list[CarSensorSpec] = [
    CarSensorSpec(
        "range_acon",
        "Range (A/C on)",
        _ev_getter("range_acon"),
        transform=_to_float,
        unit_of_measurement="km",
    ),
    CarSensorSpec(
        "range_acoff",
        "Range (A/C off)",
        _ev_getter("range_acoff"),
        transform=_to_float,
        unit_of_measurement="km",
    ),
    CarSensorSpec("soc", "State of Charge", _ev_getter("soc"), transform=_round_1, device_class=SensorDeviceClass.BATTERY, unit_of_measurement=PERCENTAGE),
    CarSensorSpec("soc_display", "State of Charge Display", _ev_getter("soc_display"), transform=_round_1, device_class=SensorDeviceClass.BATTERY, unit_of_measurement=PERCENTAGE),
    CarSensorSpec("charge_bars", "Charge Bars", _ev_getter("charge_bars")),
    CarSensorSpec("plugged_in", "Charge Cable", _ev_getter("plugged_in"), transform=_plugged_to_str),
    CarSensorSpec("charging", "Charging", _ev_getter("charging")),
    CarSensorSpec("charge_finish", "Charge Finish", _ev_getter("charge_finish")),
    CarSensorSpec("quick_charging", "Quick Charging", _ev_getter("quick_charging")),
    CarSensorSpec("ac_status", "AC Status", _ev_getter("ac_status")),
    CarSensorSpec("eco_mode", "Eco Mode", _ev_getter("eco_mode")),
    CarSensorSpec("car_running", "Running", _ev_getter("car_running")),
    CarSensorSpec("odometer", "Odometer", lambda car: car.get("odometer"), transform=_to_int, unit_of_measurement="km",),
    CarSensorSpec("full_chg_time", "Full Charge Time", _ev_getter("full_chg_time"), transform=_to_int, unit_of_measurement="min"),
    CarSensorSpec("limit_chg_time", "Limit Charge Time", _ev_getter("limit_chg_time"), transform=_to_int, unit_of_measurement="min"),
    CarSensorSpec("obc_6kw", "OBC 6kW", _ev_getter("obc_6kw"), transform=_to_int, unit_of_measurement="min"),
    CarSensorSpec("car_gear", "Gear", _ev_getter("car_gear"), transform=_to_int),
    CarSensorSpec("soh", "Battery Health", _ev_getter("soh"), transform=_round_1, unit_of_measurement=PERCENTAGE),
    CarSensorSpec("wh_content", "Remaining Energy", _ev_getter("wh_content"), transform=_to_kwh, unit_of_measurement="kWh"),
    CarSensorSpec("cap_bars", "Capacity Bars", _ev_getter("cap_bars"), transform=_to_int),
    CarSensorSpec("gids", "Available GIDs", _ev_getter("gids"), transform=_to_int),
    CarSensorSpec("counter", "Battery Counter", _ev_getter("counter"), transform=_to_int),
    CarSensorSpec("max_gids", "Maximum GIDs", _ev_getter("max_gids"), transform=_to_int),
    CarSensorSpec("param21", "Battery Parameter 21", _ev_getter("param21"), transform=_to_int),
    CarSensorSpec("cabin_temp", "Cabin Temperature", _ev_getter("cabin_temp"), transform=_to_float, unit_of_measurement="°C"),
    CarSensorSpec("force_soc_display", "Forced SOC Display", _ev_getter("force_soc_display")),
    CarSensorSpec("obc_6kw_avail", "OBC 6kW Available", _ev_getter("obc_6kw_avail")),
    CarSensorSpec("batt_heater_avail", "Battery Heater Available", _ev_getter("batt_heater_avail")),
    CarSensorSpec("batt_heater_status", "Battery Heater Active", _ev_getter("batt_heater_status")),
    CarSensorSpec("signal_level", "Signal Level", lambda car: car.get("signal_level"), transform=_to_int),
    CarSensorSpec("tpms_fl", "Tyre Pressure Front Left", _health_getter("tpms_fl"), transform=_tpms_bar, unit_of_measurement="bar"),
    CarSensorSpec("tpms_fr", "Tyre Pressure Front Right", _health_getter("tpms_fr"), transform=_tpms_bar, unit_of_measurement="bar"),
    CarSensorSpec("tpms_rl", "Tyre Pressure Rear Left", _health_getter("tpms_rl"), transform=_tpms_bar, unit_of_measurement="bar"),
    CarSensorSpec("tpms_rr", "Tyre Pressure Rear Right", _health_getter("tpms_rr"), transform=_tpms_bar, unit_of_measurement="bar"),
    CarSensorSpec("tpms_light", "TPMS Warning", _health_getter("tpms_light")),
    CarSensorSpec("maintenance_alert", "Maintenance Alert", _health_getter("maintenance_alert")),
    CarSensorSpec("health_mileage", "Health Report Mileage", _health_getter("mileage"), transform=_to_float, unit_of_measurement="km"),
]


class CarValueSensor(OpenCarwingsCarEntity, SensorEntity):
    """Generic per-car sensor based on CarSensorSpec."""

    def __init__(self, coordinator, entry_id: str, vin: str, spec: CarSensorSpec, seed_car: dict | None = None) -> None:
        OpenCarwingsCarEntity.__init__(self, coordinator, entry_id, vin, seed_car)
        self._spec = spec
        self._attr_unique_id = f"ocw_integration_{spec.key}_{vin}"
        if spec.device_class:
            self._attr_device_class = spec.device_class
        if spec.unit_of_measurement:
            self._attr_native_unit_of_measurement = spec.unit_of_measurement
        self._attr_icon = spec.icon or SENSOR_ICONS.get(spec.key)

    @property
    def name(self) -> str:
        car = self._get_car()
        prefix = car.get("nickname") or car.get("model_name") or "Car"
        return f"{prefix} {self._spec.name}"

    @property
    def native_value(self):
        car = self._get_car()
        val = self._spec.value(car)

        if self._spec.transform:
            return self._spec.transform(val)
        return val


# -----------------------------
# Status sensor 
# -----------------------------

class CarStatusSensor(OpenCarwingsCarEntity, SensorEntity):
    """High-level status string for the car (charging, running, ac_on, idle)."""

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: dict | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ocw_integration_status_{vin}"
        self._attr_icon = "mdi:car-info"

    @property
    def name(self) -> str:
        car = self._get_car()
        prefix = car.get("nickname") or car.get("model_name") or "Car"
        return f"{prefix} Status"

    @property
    def native_value(self) -> str:
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        if ev.get("charging"):
            return "charging"
        if ev.get("car_running"):
            return "running"
        if ev.get("ac_status"):
            return "ac_on"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Keep this SMALL and SAFE (optional). Remove entirely if you want no attributes.
        car = self._get_car()
        ev = car.get("ev_info", {}) or {}
        return {
            ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
            "last_connection": car.get("last_connection"),
            "signal_level": car.get("signal_level"),
            "soc": ev.get("soc"),
            "range_acoff": ev.get("range_acoff"),
        }


class CarDTCStatusSensor(OpenCarwingsCarEntity, SensorEntity):
    """Diagnostic sensor exposing the number and details of reported DTCs."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: dict | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ocw_integration_dtc_{vin}"
        self._attr_icon = "mdi:alert-circle"

    @property
    def name(self) -> str:
        car = self._get_car()
        prefix = car.get("nickname") or car.get("model_name") or "Car"
        return f"{prefix} Diagnostic Trouble Codes"

    @property
    def native_value(self) -> int:
        health = self._get_car().get("veh_health") or {}
        short = health.get("dtc_short") or []
        long = health.get("dtc_long") or []
        return len(short) + len(long) if isinstance(short, list) and isinstance(long, list) else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self._get_car().get("veh_health") or {}
        return {
            ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
            "short_codes": health.get("dtc_short") or [],
            "long_codes": health.get("dtc_long") or [],
            "timestamp": health.get("dtc_timestamp"),
        }


# -----------------------------
# Diagnostic sensors
# -----------------------------

class CarVINSensor(OpenCarwingsCarEntity, SensorEntity):
    """Per-car diagnostic sensor reporting the VIN."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: dict | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ocw_integration_vin_{vin}"
        self._attr_icon = "mdi:identifier"

    @property
    def name(self) -> str:
        car = self._get_car()
        prefix = car.get("nickname") or car.get("model_name") or "Car"
        return f"{prefix} VIN"

    @property
    def native_value(self) -> str:
        return self._vin or "unknown"


class CarLastUpdatedSensor(OpenCarwingsCarEntity, SensorEntity):
    """Diagnostic: timestamp provided by the car (ev_info.last_updated or location or last_connection)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: dict | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ocw_integration_last_updated_{vin}"
        self._attr_icon = "mdi:update"

    @property
    def name(self) -> str:
        car = self._get_car()
        prefix = car.get("nickname") or car.get("model_name") or "Car"
        return f"{prefix} Last Updated"

    @property
    def native_value(self) -> str:
        car = self._get_car()
        ev = car.get("ev_info") or {}
        loc = car.get("location") or {}
        ts = ev.get("last_updated") or loc.get("last_updated") or car.get("last_connection")
        parsed = _parse_ts(ts) if isinstance(ts, str) else None
        if parsed:
            return _format_dt(parsed) or parsed.isoformat()
        return "unknown"


class CarLastRequestedSensor(OpenCarwingsCarEntity, SensorEntity):
    """Diagnostic: last time the integration requested data from the API."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry_id: str, vin: str, seed_car: dict | None = None) -> None:
        super().__init__(coordinator, entry_id, vin, seed_car)
        self._attr_unique_id = f"ocw_integration_last_requested_{vin}"
        self._attr_icon = "mdi:clock-outline"

    @property
    def name(self) -> str:
        car = self._get_car()
        prefix = car.get("nickname") or car.get("model_name") or "Car"
        return f"{prefix} Last Requested"

    @property
    def native_value(self) -> str:
        coord = self.coordinator
        dt = getattr(coord, "last_update_time", None) if coord else None
        return _format_dt(dt) or "unknown"


# -----------------------------
# Car list sensor
# -----------------------------

class CarListSensor(SensorEntity):
    """Sensor that represents the list of cars for the account."""

    def __init__(self, entry_id: str, cars: list[dict] | None = None, coordinator=None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._cars = cars or []
        self._attr_unique_id = f"ocw_integration_{entry_id}_cars"
        self._attr_icon = "mdi:car-multiple"

    @property
    def name(self) -> str:
        return "OpenCARWINGS Cars"

    @property
    def native_value(self) -> int:
        cars = self._coordinator.data if self._coordinator and self._coordinator.data is not None else self._cars
        return len(cars)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cars = self._coordinator.data if self._coordinator and self._coordinator.data is not None else self._cars
        return {
            ATTR_ATTRIBUTION: "Data provided by OpenCARWINGS",
            "car_vins": [c.get("vin") for c in cars if c.get("vin")],
        }

    async def async_added_to_hass(self) -> None:
        if self._coordinator:
            unsub = self._coordinator.async_add_listener(self.async_write_ha_state)
            self.async_on_remove(unsub)


# -----------------------------
# Setup
# -----------------------------

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")
    cars = coordinator.data if coordinator and coordinator.data is not None else data.get("cars", [])

    entities: list[SensorEntity] = []
    entities.append(CarListSensor(entry.entry_id, cars=cars, coordinator=coordinator))

    for car in cars:
        vin = car.get("vin")
        if not vin:
            continue

        # Generic value sensors
        for spec in CAR_SENSORS:
            entities.append(CarValueSensor(coordinator, entry.entry_id, vin, spec, seed_car=car))

        # Status
        entities.append(CarStatusSensor(coordinator, entry.entry_id, vin, seed_car=car))
        entities.append(CarDTCStatusSensor(coordinator, entry.entry_id, vin, seed_car=car))

        # Diagnostics
        entities.append(CarLastUpdatedSensor(coordinator, entry.entry_id, vin, seed_car=car))
        entities.append(CarLastRequestedSensor(coordinator, entry.entry_id, vin, seed_car=car))
        entities.append(CarVINSensor(coordinator, entry.entry_id, vin, seed_car=car))

    async_add_entities(entities)
