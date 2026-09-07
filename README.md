# OpenCarWings Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/v/release/drrcastro/OCW?style=for-the-badge)](https://github.com/drrcastro/OCW/releases)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/drrcastro/OCW?style=for-the-badge)](https://github.com/drrcastro/OCW/commits/main)
[![License](https://img.shields.io/github/license/drrcastro/OCW?style=for-the-badge)](LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A lightweight Home Assistant integration that connects OpenCARWINGS to Home Assistant.

## ✨ Features

- **🚗 Full car control:** Charge, A/C, doors, horn, lights, remote start/stop.
- **🔑 Simple Authentication:** Uses Personal API Key authentication.
- **⚡ Automated Polling:** Configurable data refresh intervals.

## 📦 What it supports

### 📊 Sensors
- **Battery & Range:** State of Charge (SoC), Range (A/C on / A/C off), Remaining energy (kWh), Capacity bars, GIDs, and maximum GIDs.
- **Charging:** Plugged in status, Charging status, Quick charging, Charge finish time, and OBC status.
- **Climate & Environment:** Cabin temperature, A/C status, Eco mode, and Battery heater status.
- **Vehicle Data:** Odometer, Gear, Battery counter, and Battery parameters.
- **Health & Diagnostics:** State of Health (SoH), Tyre pressure for all four wheels (TPMS), TPMS/maintenance warnings, Diagnostic Trouble Codes (DTC), and TCU signal level.

### 📍 Device Tracker
- **GPS Location:** Tracks the car's physical location (uses `last_location` / `location` returned by the API). 

### 🎛️ Controls (Buttons & Switches)
- 🔄 **Refresh:** Request immediate data sync from the car.
- 🔋 **Charging:** Start Charge, Start Charge 80%.
- ❄️ **Climate (A/C):** Turn A/C On/Off
- 🚪 **Doors:** Unlock/Lock doors *(Requires PIN)*.
- 🔊 **Horn & Lights:** Horn, Lights, Horn & Lights, Stop Horn & Lights *(Requires PIN)*.
- 🚗 **Engine:** Remote Start, Remote Stop *(Requires PIN)*.

> **Note:** Commands marked with *(Requires PIN)* require a **command PIN** to be set in your OpenCARWINGS account portal. 

## 🔧 Installation

### Option 1: HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Go to **Integrations** → **⋮** (menu in top right) → **Custom repositories**.
3. Add the following repository URL:
   `https://github.com/drrcastro/OCW`
4. Select category: **Integration** and click **Add**.
5. Close the modal, search for **OpenCarWings** in HACS, and click **Download**.
6. **Restart Home Assistant**.
7. Go to **Settings → Devices & Services → Add Integration**.
8. Search for **OpenCarWings** and follow the setup instructions.

### Option 2: Manual Installation
1. Clone or download this repository.
2. Copy the `custom_components/ocw_integration` folder to your `<config>/custom_components/` directory on your Home Assistant host.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration**.
5. Search for **OpenCarWings** and follow the setup flow.

## ⚙️ Configuration

Setup is done entirely via the UI. You will need:

- **API Key:** Your personal API key from your OpenCARWINGS account.
  - Get it at: [OpenCARWINGS Portal](https://opencarwings.viaaq.eu) → Account Settings → API Token.
  - Copy the full token (format: `Token xxxxxxxxxxxxxx`).
- **Scan interval:** Polling frequency (default is 15 minutes).
- **API base URL:** Defaults to `https://opencarwings.viaaq.eu`.

## 🙏 Credits & Acknowledgements

- Original integration base by @czapeczek and @tomeczko.
- A huge thank you to the [OpenCARWINGS](https://github.com/developerfromjokela/opencarwings) project for providing the reverse-engineered API that makes this integration possible.
