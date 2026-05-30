# IntesisHome for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-1.0.0-blue)
![HA](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-green)

A native Home Assistant custom integration for **IntesisHome** cloud-connected AC controllers (airconwithme / anywAiR devices).

Built on the [`pyintesishome`](https://github.com/jnimmo/pyIntesisHome) library with a clean UI config flow, dynamic mode detection, and mode-based MDI icons.

---

## Features

- **UI config flow** — set up from Settings → Integrations with just your IntesisHome username and password. No YAML required.
- **Mode-based icons** — the entity icon in HA changes to reflect the active HVAC mode:

  | Mode | Icon |
  |------|------|
  | Cool | `mdi:snowflake` ❄️ |
  | Heat | `mdi:white-balance-sunny` ☀️ |
  | Dry | `mdi:water-off` 💧 |
  | Fan only | `mdi:fan` 🌀 |
  | Auto | `mdi:cached` 🔄 |
  | Off | *(default thermostat icon)* |

- **Dynamic mode detection** — supported HVAC modes are read directly from your device at setup, so only modes your AC actually supports appear in HA.
- **Fan speed control** — quiet, low, medium, high, auto (device-dependent).
- **Vertical & horizontal swing** — full vane position control where supported.
- **Preset modes** — eco, comfort, and powerful/boost where supported.
- **Extra state attributes** — outdoor temperature, heating power consumption (kW), cooling power consumption (kW).
- **Cloud push** — the integration maintains a persistent connection to the IntesisHome cloud and receives state updates in real time without polling.

---

## Requirements

- Home Assistant **2024.1** or newer
- An active [IntesisHome](https://www.intesishome.com) / airconwithme / anywAiR account
- `pyintesishome==2.0.1` (installed automatically)

---

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add `https://github.com/Fahed-Alhammadi/IntesisHome` as an **Integration**
4. Search for **IntesisHome** and install it
5. Restart Home Assistant

### Manual

1. Download the latest release zip from the [Releases](https://github.com/Fahed-Alhammadi/IntesisHome/releases) page
2. Extract and copy the `custom_components/intesishome/` folder into your HA `config/custom_components/` directory
3. Restart Home Assistant

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **IntesisHome**
3. Enter your IntesisHome **username** and **password**
4. Each AC unit linked to your account will appear as a separate climate device

---

## File Structure

```
custom_components/intesishome/
├── __init__.py            # Integration setup and teardown
├── climate.py             # ClimateEntity with mode-based icons
├── config_flow.py         # UI config flow (username + password)
├── manifest.json          # Integration metadata
├── strings.json           # UI string keys
└── translations/
    └── en.json            # English labels
```

---

## Debugging

To enable debug logging, add the following to your `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    custom_components.intesishome: debug
    pyintesishome: debug
```

Then restart Home Assistant and reproduce the issue. Logs can be downloaded from **Settings → System → Logs**.

---

## Credits

- Based on the excellent work of [@jnimmo](https://github.com/jnimmo) in [hass-intesishome](https://github.com/jnimmo/hass-intesishome) and [pyIntesisHome](https://github.com/jnimmo/pyIntesisHome)
- Maintained by [@Fahed-Alhammadi](https://github.com/Fahed-Alhammadi)

---

## License

MIT License — see [LICENSE](LICENSE) for details.
