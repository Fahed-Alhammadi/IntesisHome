# IntesisHome — Native Home Assistant Integration

A clean, native HA custom integration for IntesisHome, anywAiR, airconwithme,
IntesisBox, and IntesisHome Local devices. Built on top of the `pyintesishome`
library with a full UI config flow and mode-based MDI icons.

## Features

- **UI config flow** — set up from Settings → Integrations, no YAML needed
- **Mode-based icons** — entity icon changes with the active HVAC mode:
  | Mode | Icon |
  |------|------|
  | Cool | `mdi:snowflake` ❄️ |
  | Heat | `mdi:white-balance-sunny` ☀️ |
  | Dry | `mdi:water-off` 💧 |
  | Fan only | `mdi:fan` 🌀 |
  | Auto / Heat-Cool | `mdi:cached` 🔄 |
  | Off | *(default thermostat icon)* |
- **Dynamic mode detection** — supported modes read directly from the device
- **Full climate features** — fan speed, vertical & horizontal swing, presets (eco / comfort / powerful)
- **Outdoor temp** and **power consumption** exposed as extra state attributes
- Supports all device types: IntesisHome (cloud), anywAiR, airconwithme, IntesisBox (local), IntesisHome Local HTTP

## Installation

### HACS (recommended)
1. Add this repo as a custom repository in HACS
2. Install **IntesisHome**
3. Restart Home Assistant

### Manual
1. Copy `custom_components/intesishome/` into your HA `config/custom_components/` folder
2. Restart Home Assistant

## Setup
1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **IntesisHome**
3. Select your device type and enter credentials

## File Structure

```
custom_components/intesishome/
├── __init__.py          # Integration setup / teardown
├── climate.py           # ClimateEntity with icon-per-mode
├── config_flow.py       # UI config flow (2-step)
├── manifest.json        # Integration metadata
├── strings.json         # UI string keys
└── translations/
    └── en.json          # English labels
```

## Requirements

- Home Assistant 2024.1+
- `pyintesishome==2.0.1` (installed automatically)
