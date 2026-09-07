# OpenCARWINGS Home Assistant Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Community Forum][forum-shield]][forum]
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Lightweight Home Assistant integration that connects to the OpenCARWINGS API to expose your Nissan (or compatible) cars as devices in Home Assistant.

**Features:**
- 🚗 Full car control: charge, A/C, doors, horn, lights, remote start/stop
- 🔑 Simple API Key authentication (no password storage)
- 📊 Real-time sensor data: battery, range, charging status, location
- 🎛️ Easy setup via UI integration flow
- ⚡ Automatic data refresh with configurable intervals


---

## What it supports ✅

Per car the integration currently exposes:

- Sensors
  - Range (A/C on / A/C off)
  - Charge cable plugged in (plugged / unplugged)
  - High-level status (charging / running / ac_on / idle)
  - **Per-car "Last Updated"** (diagnostic): reports the ISO 8601 timestamp of the last direct reading from the car. The sensor is created per VIN, shows the most recent timestamp found in `ev_info.last_updated`, `location.last_updated`, or `last_connection`, and has the unique id pattern `ha_opencarwings_last_updated_<VIN>`.
  - **Per-car "Last Requested"** (diagnostic): reports the last time the integration requested data from the API (coordinator's last update time). The sensor is created per VIN and has the unique id pattern `ha_opencarwings_last_requested_<VIN>`.
  - A top-level `OpenCARWINGS Cars` sensor listing your cars and VINs
- Device tracker: car GPS (uses `last_location` / `location` returned by the API). The tracker entity is attached to the same car device as the per-car buttons and shares the car VIN as the device identifier; the tracker entity itself keeps a stable `unique_id` of the form `ha_opencarwings_tracker_<VIN>`. The visible name prefers the car's `nickname` if present, otherwise it falls back to `model_name` (for example, "MyCar Tracker").
- Switch: A/C control (on/off) — sends commands to the car via the OpenCARWINGS command endpoint
- Buttons: **Full car control** — send any command available on the OpenCARWINGS API:
  - 🔄 **Data refresh** — request immediate data sync from the car
  - 🔋 **Charge commands** — Charge start, Charge start 80%
  - ❄️ **Climate** — A/C on, A/C off (also available as switch)
  - 🚪 **Door control** — Unlock/Lock doors (requires PIN)
  - 🔊 **Horn & Lights** — Horn, Lights, Horn & Lights, Stop (requires PIN)
  - 🚗 **Engine control** — Remote Start, Remote Stop (requires PIN)
  - ℹ️ **Integration button** — Manual refresh for all cars (unique id: `ha_opencarwings_refresh_<entry_id>`)

---

## History & Recorder ⚠️

The per-car **Last Updated** sensors are marked as diagnostic (they're metadata, not a regularly changing state) and are typically not recorded by Home Assistant's Recorder. If you want to ensure these sensors are excluded from history/recorder, add an exclusion to your `configuration.yaml`:

```yaml
recorder:
  exclude:
    entity_globs:
      - "sensor.ha_opencarwings_last_updated_*"
      - "sensor.ha_opencarwings_last_requested_*"
```

This will prevent per-car `Last Updated` sensors from being stored in your database and showing up in history charts.

---

## Entity names & unique IDs 🔎

A few helpful naming/ID patterns to identify entities created by the integration:

- Device tracker name: uses `nickname` when available, otherwise `model_name`. Visible name example: `MyCar Tracker`.
- Tracker unique_id: `ha_opencarwings_tracker_<VIN>`
- Tracker device identifier: `tracker_<VIN>` (the tracker appears as a separate device; the entity unique id above still applies)
- Per-car "Last Updated" sensor: `ha_opencarwings_last_updated_<VIN>`
- Car refresh button label: `Request data refresh for <nickname|model>` (visible name) — unique id: `ha_opencarwings_car_refresh_<VIN>`
- A/C switch: `ha_opencarwings_ac_<VIN>`

These stable IDs are useful when excluding entities from the recorder or when writing automations targeting specific cars.

These entities are created per-VIN and appear as devices in the Integrations UI.

---

## Installation 🔧

### Option 1: HACS (Recommended)
1. Open **HACS** in Home Assistant
2. Go to **Integrations** → **⋯** (menu) → **Custom repositories**
3. Add repository:
   ```
   https://github.com/drrcastro/ha_opencarwings
   ```
4. Select category: **Integration**
5. Click **Create** → Find **OpenCARWINGS** → **Install**
6. **Restart Home Assistant**
7. Go to **Settings → Devices & Services → Create Integration**
8. Search for **OpenCARWINGS** and follow setup

### Option 2: Manual Installation
1. Download the repository or clone it:
   ```bash
   git clone https://github.com/drrcastro/ha_opencarwings.git
   ```
2. Copy `custom_components/ha_opencarwings` to `<config>/custom_components/` on your Home Assistant host
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration**
5. Search for **OpenCARWINGS** and follow the setup flow

---

## Configuration ⚙️

Setup is done via the UI. You will need:

### Authentication
- **API Key** — Personal API key from your OpenCARWINGS account
  - 🔗 Get it at: [https://opencarwings.viaaq.eu](https://opencarwings.viaaq.eu) → Account Settings → API Token
  - Copy the full token (format: `Token xxxxxxxxxxxxxx`)
  - ✅ Works with 2FA enabled
  - ✅ No password storage needed

### Options
- **Scan interval** (polling frequency, default: 15 minutes). The setup and options flows present a friendly select with labeled choices (for example: "1 minute", "15 minutes (default)", "1 hour", "1 day").
- **API base URL** (optional — defaults to `https://opencarwings.viaaq.eu`)

### Commands Requiring PIN
Some commands (door unlock/lock, horn, lights, remote start/stop) require a **command PIN** to be set in your OpenCARWINGS account portal. This is a security measure to prevent unauthorized access.

---

## Development & Tests 🧪

- Run tests with: `pytest`
- The repository includes Home Assistant test stubs under `tests/stubs/` to make running unit tests easier.

---

## Reporting issues & Contributing 🤝

Found a bug or want a feature? Please open an issue or a PR at: https://github.com/drrcastro/ha_opencarwings

Contributions, fixes and improvements are welcome!

### Recent Updates 📝
- ✅ Full car control commands (all 13 types)
- ✅ API Key authentication (simpler setup)
- ✅ Automatic PIN handling for secure commands
- ✅ Per-car command buttons
- ✅ A/C control via switch or button

---

## Thank you 🙏

A big thank you to the OpenCARWINGS project for providing the reverse-engineered API that makes this integration possible: https://github.com/developerfromjokela/opencarwings

<!-- Badges -->
[releases-shield]: https://img.shields.io/github/v/release/drrcastro/ha_opencarwings?style=for-the-badge
[releases]: https://github.com/drrcastro/ha_opencarwings/releases

[commits-shield]: https://img.shields.io/github/commit-activity/y/drrcastro/ha_opencarwings?style=for-the-badge
[commits]: https://github.com/drrcastro/ha_opencarwings/commits/main

[license-shield]: https://img.shields.io/github/license/drrcastro/ha_opencarwings?style=for-the-badge

[maintenance-shield]: https://img.shields.io/badge/maintained-yes-green.svg?style=for-the-badge

[buymecoffeebadge]: https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-yellow.svg?style=for-the-badge
[buymecoffee]: https://www.buymeacoffee.com/czapeczek

[forum-shield]: https://img.shields.io/badge/community-forum-blue.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[hacs-repo-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-install]: https://my.home-assistant.io/redirect/hacs_repository/?owner=drrcastro&repository=ha_opencarwings&category=Integration
