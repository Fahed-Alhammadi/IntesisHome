# IntesisHome for Home Assistant

## Overview
HACS custom integration connecting IntesisHome cloud AC controllers (airconwithme / anywAiR) to Home Assistant. Cloud-push: keeps a persistent TCP connection to the IntesisHome cloud via `pyintesishome` and receives state updates in real time.

## Structure
- `custom_components/intesishome/__init__.py` — config entry setup/teardown, connection health check + runtime reauth trigger
- `custom_components/intesishome/climate.py` — `IntesisAC` ClimateEntity (modes, fan, swing, presets, mode-based icons)
- `custom_components/intesishome/sensor.py` — outdoor temp, heat/cool power (kW), Wi-Fi RSSI (diagnostic) sensors
- `custom_components/intesishome/config_flow.py` — UI config flow + reauth (username/password)
- `custom_components/intesishome/strings.json` + `translations/en.json` — UI strings (keep both in sync)
- `manifest.json` — version lives here (also mirrored in README badge)
- `hacs.json` — HACS metadata, min HA 2024.12

## Tech Stack
Python (HA 2024.12+, so 3.12+ syntax incl. `type` aliases), `pyintesishome==2.0.2`, Home Assistant core APIs.

## Commands
- Syntax check: `python3 -m py_compile custom_components/intesishome/*.py` (needs Python 3.12+; system 3.9 chokes on the `type` alias in `__init__.py`)
- JSON check: `python3 -c "import json; json.load(open('<file>'))"`
- No test suite; validation is manual in a HA instance.

## Conventions
- Entities are push-based: `_attr_should_poll = False`, `PARALLEL_UPDATES = 0`, controller update callbacks registered in `async_added_to_hass`.
- Never call `controller.stop()` from entities — the controller is shared via `entry.runtime_data`; only `async_unload_entry` stops it.
- Commands verify the cloud ACK via `_expect_ack` and raise `HomeAssistantError` on failure.
- `MIN_TEMP_LIMIT = 16.0` in climate.py caps the reported minimum setpoint (cloud often claims 18 °C; units accept 16 °C). Cap only widens the range.
- pyintesishome 2.0.2 auto-reconnects with backoff BUT permanently stops retrying on auth errors — the 5-min health check in `__init__.py` covers that gap and starts reauth.
- Version bumps: update `manifest.json` and the README badge together.

## Change Log
- 2026-07-19: v1.2.0 — min setpoint capped at 16 °C (was device-reported, typically 18); added connection health check with runtime reauth; added Wi-Fi RSSI diagnostic sensor; exposed rssi/run_hours as climate attributes; fixed falsy-temperature skip in `async_set_temperature`; guarded unknown preset modes; `PARALLEL_UPDATES = 0`; controller stopped if platform setup fails.
- 2026-07-19 and earlier: v1.1.x — initial config flow, climate + sensor platforms, reauth flow, mode-based icons.
