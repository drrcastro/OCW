"""Button platform providing a manual refresh button for OpenCARWINGS."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from typing import Any

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    # Create a single per-entry refresh button
    entities = [OpenCarWingsRefreshButton(entry.entry_id, coordinator=coordinator)]

    # Create per-car command buttons for each car
    cars = data.get("cars", [])
    for car in cars:
        if car.get("vin"):
            # Data refresh and charging commands
            entities.append(CarRefreshButton(entry.entry_id, car))
            entities.append(CarChargeStartButton(entry.entry_id, car))
            entities.append(CarChargeStart80Button(entry.entry_id, car))
            
            # Climate control
            entities.append(CarACOnButton(entry.entry_id, car))
            entities.append(CarACOffButton(entry.entry_id, car))
            
            # Horn and lights
            entities.append(CarHornButton(entry.entry_id, car))
            entities.append(CarLightsButton(entry.entry_id, car))
            entities.append(CarHornLightsButton(entry.entry_id, car))
            entities.append(CarStopHornLightsButton(entry.entry_id, car))
            
            # Door control (requires PIN)
            entities.append(CarDoorUnlockButton(entry.entry_id, car))
            entities.append(CarDoorLockButton(entry.entry_id, car))
            
            # Engine control (requires PIN)
            entities.append(CarRemoteStartButton(entry.entry_id, car))
            entities.append(CarRemoteStopButton(entry.entry_id, car))

    # Tests set hass on the entity for direct method calls
    for ent in entities:
        ent.hass = hass

    async_add_entities(entities)


class OpenCarWingsRefreshButton(ButtonEntity):
    """Button that triggers a coordinator refresh when pressed."""

    def __init__(self, entry_id: str, coordinator=None) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator

    @property
    def name(self) -> str:
        return "OpenCARWINGS Refresh"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_refresh_{self._entry_id}"

    async def async_press(self) -> None:
        """Press the button to force an immediate coordinator refresh."""
        if not self._coordinator:
            _LOGGER.warning("Refresh button pressed but coordinator is not available for %s", self._entry_id)
            return
        try:
            await self._coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - network or unexpected
            _LOGGER.exception("Failed to refresh OpenCARWINGS data for %s", self._entry_id)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id}


class CarRefreshButton(ButtonEntity):
    """Button that sends a 'Refresh data' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")

    @property
    def name(self) -> str:
        # Friendly label: prefer car nickname, then model name, then VIN
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Request data refresh for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_refresh_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        """Press the button to send a 'Refresh data' command to the API for this car."""
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_request(
                "POST",
                f"/api/command/{self._vin}/",
                json={"vin": self._vin, "command_type": 1},
            )
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to request car refresh for %s", self._vin)
            raise

        # After a successful API request, trigger the coordinator to refresh so
        # the integration's coordinator.last_update_time is updated and the
        # per-car Last Requested diagnostic sensor will reflect the request time.
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - coordinator failure
            _LOGGER.exception("Failed to trigger coordinator refresh after requesting car refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


def hass_client(hass, entry_id: str):
    """Helper to get the API client stored in hass.data."""
    return hass.data[DOMAIN][entry_id]["client"]


class CarChargeStartButton(ButtonEntity):
    """Button that sends a 'Charge start' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 2  # Charge start

    @property
    def name(self) -> str:
        # Friendly label: prefer car nickname, then model name, then VIN
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Charge start for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_chargestart_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        """Press the button to send a 'Charge start' command to the API for this car."""
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_send_command(self._vin, self._command_type)
        except Exception:  # pragma: no cover - network
            _LOGGER.exception("Failed to send command %s for %s", self._command_type, self._vin)
            raise

        # Trigger a coordinator refresh after sending the command
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:  # pragma: no cover - coordinator failure
            _LOGGER.exception("Failed to trigger coordinator refresh after command for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarChargeStart80Button(ButtonEntity):
    """Button that sends a 'Charge start 80%' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 6  # Charge start 80%

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Charge start 80% for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_chargestart80_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_send_command(self._vin, self._command_type)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarACOnButton(ButtonEntity):
    """Button that sends 'A/C on' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 3  # A/C on

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"A/C on for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_ac_on_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_send_command(self._vin, self._command_type)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarACOffButton(ButtonEntity):
    """Button that sends 'A/C off' command for a specific car."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 4  # A/C off

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"A/C off for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_ac_off_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            await client.async_send_command(self._vin, self._command_type)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarHornButton(ButtonEntity):
    """Button that sends 'Horn' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 9  # Horn

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Horn for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_horn_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            # Note: requires command_pin in account settings or via helper_pin input
            pin = None  # User must set PIN in account settings on OpenCARWINGS portal
            await client.async_send_command(self._vin, self._command_type, pin)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarLightsButton(ButtonEntity):
    """Button that sends 'Lights' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 10  # Lights

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Lights for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_lights_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = None  # User must set PIN in account settings on OpenCARWINGS portal
            await client.async_send_command(self._vin, self._command_type, pin)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarHornLightsButton(ButtonEntity):
    """Button that sends 'Horn & Lights' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 11  # Horn & Lights

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Horn & Lights for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_horn_lights_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = None  # User must set PIN in account settings on OpenCARWINGS portal
            await client.async_send_command(self._vin, self._command_type, pin)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarStopHornLightsButton(ButtonEntity):
    """Button that sends 'Stop Horn & Light' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 12  # Stop Horn & light

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Stop Horn & Lights for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_stop_horn_lights_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = None  # User must set PIN in account settings on OpenCARWINGS portal
            await client.async_send_command(self._vin, self._command_type, pin)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarDoorUnlockButton(ButtonEntity):
    """Button that sends 'Door unlock' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 7  # Door unlock

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Unlock doors for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_door_unlock_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = None  # User must set PIN in account settings on OpenCARWINGS portal
            await client.async_send_command(self._vin, self._command_type, pin)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarDoorLockButton(ButtonEntity):
    """Button that sends 'Door lock' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 8  # Door lock

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Lock doors for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_door_lock_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = None  # User must set PIN in account settings on OpenCARWINGS portal
            await client.async_send_command(self._vin, self._command_type, pin)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarRemoteStartButton(ButtonEntity):
    """Button that sends 'Remote Start' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 13  # Remote Start

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Remote start for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_remote_start_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = None  # User must set PIN in account settings on OpenCARWINGS portal
            await client.async_send_command(self._vin, self._command_type, pin)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}


class CarRemoteStopButton(ButtonEntity):
    """Button that sends 'Remote Stop' command for a specific car (requires PIN)."""

    def __init__(self, entry_id: str, car: dict) -> None:
        self._entry_id = entry_id
        self._car = car
        self._vin = car.get("vin")
        self._command_type = 14  # Remote Stop

    @property
    def name(self) -> str:
        label = self._car.get("nickname") or self._car.get("model_name") or self._vin
        return f"Remote stop for {label}"

    @property
    def unique_id(self) -> str:
        return f"ha_opencarwings_car_remote_stop_{self._vin}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": self._car.get("model_name"),
            "manufacturer": self._car.get("make"),
            "model": self._car.get("model_name"),
        }

    async def async_press(self) -> None:
        client = hass_client(self.hass, self._entry_id)
        try:
            pin = None  # User must set PIN in account settings on OpenCARWINGS portal
            await client.async_send_command(self._vin, self._command_type, pin)
        except Exception:
            _LOGGER.exception("Failed to send command for %s", self._vin)
            raise
        try:
            coordinator = self.hass.data[DOMAIN][self._entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        except Exception:
            _LOGGER.exception("Failed to trigger coordinator refresh for %s", self._vin)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"entry_id": self._entry_id, "vin": self._vin}
