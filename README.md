<div align="center">

# IntesisHome for Home Assistant

**Control IntesisHome, airconwithme and anywAiR air conditioners from Home Assistant.**

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-2.0.2-blue.svg?style=for-the-badge)](https://github.com/Fahed-Alhammadi/IntesisHome/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12%2B-41BDF5.svg?style=for-the-badge&logo=homeassistant&logoColor=white)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

[Installation](#installation) · [Setup](#setup) · [Entities](#entities) · [Troubleshooting](#troubleshooting) · [Report a bug](https://github.com/Fahed-Alhammadi/IntesisHome/issues)

</div>

---

A Home Assistant custom integration for air conditioners connected through the **IntesisHome**, **airconwithme** or **anywAiR** cloud services.

Set it up from the UI, control each AC unit as a climate entity, and get sensors, binary sensors and a filter-reset button for whatever your unit reports. Built on [`pyintesishome`](https://github.com/jnimmo/pyIntesisHome).

---

## Contents

- [Features](#features)
- [Entities](#entities)
- [Requirements](#requirements)
- [Installation](#installation)
- [Setup](#setup)
- [How it works](#how-it-works)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Removal](#removal)
- [Project structure](#project-structure)
- [Contributing](#contributing)
- [Credits](#credits)
- [License](#license)

---

## Features

- **UI setup**: pick your cloud service (IntesisHome, airconwithme or anywAiR) and sign in. No YAML needed.
- **Full climate control**: HVAC mode, target temperature, fan speed, vertical and horizontal swing (vane positions) and presets.
- **Only what your unit supports**: HVAC modes, fan speeds, swing positions and presets are read from the device and kept up to date, so HA never offers options your AC can't do.
- **Icons that follow the mode**: the climate entity's icon changes with the active HVAC mode.
- **Energy and diagnostics**: outdoor temperature, heating and cooling power (kW, with long-term statistics), Wi-Fi signal, error code and filter status.
- **One device per AC unit**: all entities for a unit are grouped under one device in the device registry, so you can assign it to an area.
- **Recovers on its own**: connection errors are retried in the background. If your password is rejected, Home Assistant asks you to re-enter it, and you don't need to remove the integration.
- **Reliable commands**: every command is checked against the cloud's reply. If the cloud rejects it, you get an error in HA rather than a silent failure.

---

## Entities

Each AC unit creates the entities below. Entities other than the climate entity are only created if the unit reports that value.

### Climate

| Feature | Values |
|---|---|
| HVAC modes | Off, Heat, Cool, Dry, Fan only, Auto *(device-dependent)* |
| Fan modes | Quiet, Low, Medium, High, Auto *(device-dependent)* |
| Swing | Vertical and horizontal vane positions *(where supported)* |
| Presets | Eco, Comfort, Boost (Powerful) *(where supported)* |
| Extra attributes | `rssi` (Wi-Fi signal), `run_hours` |

Mode-based icons:

| Mode | Icon |
|---|---|
| Cool | `mdi:snowflake` |
| Heat | `mdi:white-balance-sunny` |
| Dry | `mdi:water-off` |
| Fan only | `mdi:fan` |
| Auto | `mdi:cached` |
| Off | default thermostat icon |

### Sensors

| Entity | Unit | Category | Enabled by default |
|---|---|---|---|
| Outdoor temperature | °C | — | ✅ |
| Heating power consumption | kW | — | ✅ |
| Cooling power consumption | kW | — | ✅ |
| Wi-Fi signal strength | dBm | Diagnostic | ✅ |
| Filter due | h | Diagnostic | ✅ |
| Error code | — | Diagnostic | ❌ |

### Binary sensors

| Entity | Meaning | Category |
|---|---|---|
| Problem | The unit is reporting an alarm | Diagnostic |
| Filter | The filter needs cleaning | Diagnostic |
| Connectivity | The cloud has fresh data for the unit | Diagnostic |

### Buttons

| Entity | Action | Category |
|---|---|---|
| Reset filter | Clears the filter-clean reminder on the unit | Configuration |

---

## Requirements

- Home Assistant **2024.12** or newer
- An active [IntesisHome](https://www.intesishome.com), airconwithme or anywAiR account with at least one AC unit linked to it
- [`pyintesishome`](https://pypi.org/project/pyintesishome/) **2.5.0** (Home Assistant installs it automatically)

---

## Installation

### HACS (recommended)

1. Open **HACS** in Home Assistant.
2. Open the three-dot menu → **Custom repositories**.
3. Add `https://github.com/Fahed-Alhammadi/IntesisHome` with the type **Integration**.
4. Search for **IntesisHome** and click **Download**.
5. Restart Home Assistant.

### Manual

1. Download the latest release from the [Releases](https://github.com/Fahed-Alhammadi/IntesisHome/releases) page.
2. Copy the `custom_components/intesishome/` folder into your Home Assistant `config/custom_components/` folder.
3. Restart Home Assistant.

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **IntesisHome**.
3. Pick the **cloud service** your account uses (IntesisHome, airconwithme or anywAiR).
4. Enter your **username** and **password**.

Each AC unit linked to the account appears as its own device.

If your password changes, Home Assistant shows a re-authentication prompt once the cloud rejects the old one (checked every 5 minutes).

---

## How it works

- **Updates**: the integration fetches device state from the cloud about every **2 minutes**. Entities update as soon as new data arrives, and Home Assistant never polls them itself.
- **Commands**: changes made in Home Assistant show up right away. Changes made with the remote control or the vendor app show up on the next update, within about 2 minutes.
- **IntesisHome service**: commands are sent through the IntesisHome web portal. This avoids the command socket, which stopped acknowledging commands in September 2026.
- **airconwithme / anywAiR**: commands are sent over the cloud command socket.
- **Health check**: every 5 minutes the integration checks whether the cloud has rejected your credentials. If it has, it starts the re-authentication flow.

---

## Known limitations

- **Cloud only**: no local control. If the vendor's cloud is down, the units can't be controlled from Home Assistant.
- **Up to ~2 minutes delay** before changes made outside Home Assistant appear.
- **Minimum setpoint**: the lowest target temperature offered is **18 °C**, or the unit's own minimum if that is lower.
- **Capabilities reported late**: if a unit starts reporting a sensor value after setup, reload the integration to create that entity.

---

## Troubleshooting

| Symptom | What to try |
|---|---|
| `invalid_auth` during setup | Check the username and password, and make sure the right **cloud service** is selected. |
| `no_devices` during setup | Link the unit to your account in the vendor app first. |
| Entities are unavailable | The cloud may be unreachable. The integration keeps retrying; check the **Connectivity** binary sensor and the logs. |
| A command fails with an error | The cloud didn't accept the command. Try again; if it keeps failing, enable debug logging (below) and open an issue. |
| State changed with the remote isn't shown yet | Wait up to ~2 minutes for the next cloud update. |

### Debug logging

Add this to `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  default: warning
  logs:
    custom_components.intesishome: debug
    pyintesishome: debug
```

Reproduce the issue, then download the logs from **Settings → System → Logs**. Remove usernames, passwords and device IDs before sharing logs in an issue.

---

## Removal

1. Go to **Settings → Devices & Services → IntesisHome**, open the menu and choose **Delete**.
2. If you installed it with HACS, remove it in HACS as well. If you installed it manually, delete `config/custom_components/intesishome/`.
3. Restart Home Assistant.

---

## Project structure

```
custom_components/intesishome/
├── __init__.py            # Setup/teardown, command handling, health check
├── entity.py              # Shared base class for sensors, binary sensors and buttons
├── climate.py             # Climate entity (modes, fan, swing, presets, icons)
├── sensor.py              # Temperature, power, Wi-Fi, error code and filter sensors
├── binary_sensor.py       # Problem, filter and connectivity binary sensors
├── button.py              # Reset filter button
├── config_flow.py         # UI setup and re-authentication
├── manifest.json          # Integration metadata (version, requirements)
├── strings.json           # UI strings
└── translations/
    └── en.json            # English translations
```

---

## Contributing

Bug reports and pull requests are welcome.

- **Bugs and feature requests**: open an [issue](https://github.com/Fahed-Alhammadi/IntesisHome/issues). Include your Home Assistant version, the integration version, your cloud service and debug logs.
- **Pull requests**:
  1. Fork the repository and create a branch.
  2. Keep `strings.json` and `translations/en.json` in sync.
  3. Check syntax with `python3 -m py_compile custom_components/intesishome/*.py` (Python 3.12+).
  4. Test the change in a real Home Assistant instance. The project has no automated test suite yet.
  5. When releasing, bump the version in `manifest.json` and in the README badge together.

---

## Credits

- Based on the work of [@jnimmo](https://github.com/jnimmo) in [hass-intesishome](https://github.com/jnimmo/hass-intesishome) and [pyIntesisHome](https://github.com/jnimmo/pyIntesisHome).
- Maintained by [@Fahed-Alhammadi](https://github.com/Fahed-Alhammadi).

This project is not affiliated with or endorsed by Intesis, HMS Networks, airconwithme or anywAiR.

---

## License

Released under the MIT License. See [LICENSE](LICENSE) for details.

© 2026 Fahed Alhammadi. All rights reserved.
