from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .api import OpenCarWingsAPI, AuthenticationError, DEFAULT_API_BASE

# Scan interval choices in minutes with friendly labels
SCAN_INTERVAL_CHOICES = [
    (1, "1 minute"),
    (5, "5 minutes"),
    (10, "10 minutes"),
    (15, "15 minutes (default)"),
    (30, "30 minutes"),
    (60, "1 hour"),
    (180, "3 hours"),
    (360, "6 hours"),
    (720, "12 hours"),
    (1440, "1 day"),
]
# Values used when selector is not available (fallback)
SCAN_INTERVAL_OPTIONS = [c[0] for c in SCAN_INTERVAL_CHOICES]
DEFAULT_SCAN_INTERVAL_MIN = 15

# Default API base URL
DEFAULT_API_BASE_URL = DEFAULT_API_BASE


class ConfigFlow(config_entries.ConfigFlow, domain="ocw_integration"):
    """Config flow for OpenCARWINGS."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return the flow used by Home Assistant's Configure button."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step where user provides API key."""
        errors = {}
        if user_input is not None:
            api_key = user_input.get("api_key", "").strip()
            api_base = user_input.get("api_base_url", DEFAULT_API_BASE_URL).strip()
            scan_int = int(user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN))

            if not api_key:
                errors["api_key"] = "required"
            else:
                client = OpenCarWingsAPI(getattr(self, "hass", None), base_url=api_base)
                try:
                    await client.async_validate_api_key(api_key)
                except AuthenticationError:
                    errors["base"] = "auth"
                except Exception:  # pragma: no cover - fallback
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title="OpenCarWings",
                        data={
                            "api_key": api_key,
                            "command_pin": user_input.get("command_pin", "").strip(),
                            # persist initial scan interval choice
                            "scan_interval": scan_int,
                            "api_base_url": api_base,
                        },
                    )

        # Prefer to show a pretty select when Home Assistant's selector helpers
        # are available; fall back to a numeric choice list otherwise.
        try:
            from homeassistant.helpers import selector

            scan_selector = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=str(v), label=l)
                        for v, l in SCAN_INTERVAL_CHOICES
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        except Exception:
            # selector not available in minimal test stubs — use numeric options
            scan_selector = vol.In([str(c[0]) for c in SCAN_INTERVAL_CHOICES])

        data_schema = vol.Schema(
            {
                vol.Required("api_key"): str,
                vol.Optional("command_pin", default=""): str,
                vol.Required("scan_interval", default=str(DEFAULT_SCAN_INTERVAL_MIN)): scan_selector,
                vol.Required("api_base_url", default=DEFAULT_API_BASE_URL): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize options flow."""
        if config_entry is not None:
            self._config_entry = config_entry

    @property
    def _entry(self) -> config_entries.ConfigEntry | None:
        """Return the config entry across different Home Assistant versions."""
        if hasattr(self, "config_entry") and self.config_entry is not None:
            return self.config_entry
        return getattr(self, "_config_entry", None)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            scan_int = int(user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN))
            return self.async_create_entry(
                title="",
                data={
                    "command_pin": user_input.get("command_pin", "").strip(),
                    "scan_interval": scan_int,
                    "api_base_url": user_input.get("api_base_url", DEFAULT_API_BASE_URL).strip(),
                },
            )

        entry = self._entry
        current_scan = str(
            entry.options.get("scan_interval", entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL_MIN))
            if entry
            else DEFAULT_SCAN_INTERVAL_MIN
        )
        current_api = (
            entry.options.get("api_base_url", entry.data.get("api_base_url", DEFAULT_API_BASE_URL))
            if entry
            else DEFAULT_API_BASE_URL
        )
        current_pin = (
            entry.options.get("command_pin", entry.data.get("command_pin", ""))
            if entry
            else ""
        )
        try:
            from homeassistant.helpers import selector

            scan_selector = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=str(v), label=l)
                        for v, l in SCAN_INTERVAL_CHOICES
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        except Exception:
            scan_selector = vol.In([str(c[0]) for c in SCAN_INTERVAL_CHOICES])

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("command_pin", default=current_pin): str,
                vol.Required("scan_interval", default=current_scan): scan_selector,
                vol.Required("api_base_url", default=current_api): str,
            }),
        )
