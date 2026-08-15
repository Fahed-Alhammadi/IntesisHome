# IntesisHome for Home Assistant

## Overview
HACS custom integration connecting IntesisHome cloud AC controllers (airconwithme / anywAiR) to Home Assistant. Cloud-push: keeps a persistent TCP connection to the IntesisHome cloud via `pyintesishome` and receives state updates in real time.

## Structure
- `custom_components/intesishome/__init__.py` — config entry setup/teardown, connection health check + runtime reauth trigger
- `custom_components/intesishome/climate.py` — `IntesisAC` ClimateEntity (modes, fan, swing, presets, mode-based icons)
- `custom_components/intesishome/sensor.py` — outdoor temp, heat/cool power (kW), Wi-Fi RSSI, error code (disabled by default), filter due hours (diagnostic) sensors
- `custom_components/intesishome/binary_sensor.py` — problem (alarm_status), filter clean, connectivity (diagnostic) binary sensors
- `custom_components/intesishome/button.py` — reset filter button (writes raw UID 184 via `_set_value`, no COMMAND_MAP entry exists for it)
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
- `MIN_TEMP_LIMIT` in climate.py caps the reported minimum setpoint and is the fallback before the device reports one. Currently 18.0 (user preference; was briefly 16.0). Cap only widens the range; the cloud accepts unclamped setpoints if lowered.
- pyintesishome 2.0.2 auto-reconnects with backoff BUT permanently stops retrying on auth errors — the 5-min health check in `__init__.py` covers that gap and starts reauth.
- `controller.connect()` returns once the cloud login succeeds — it does NOT wait for the full initial device-capability push (modes/swing/fan lists) that streams in afterward. Any capability-derived entity attribute (`hvac_modes`, swing/fan lists, preset/target-temp feature bits) must be recomputed on every `async_update()` (see `IntesisAC._refresh_capabilities()` in climate.py), never just once in `__init__`, or it can freeze on incomplete data.
- Version bumps: update `manifest.json` and the README badge together.

## Change Log
- 2026-08-15: v1.1.10 — re-bumped `pyintesishome` 2.0.3 → 2.2.0 (the latest release on PyPI). Confirmed earlier this session that `const.py` and `intesishome.py` (the cloud `IntesisHome` class this integration uses) are byte-identical between 2.0.3 and 2.2.0 — the only diff is `last_successful_update` staleness tracking added to `IntesisHomeLocal`, which this cloud-only integration doesn't touch — so this reverts the brief 2.0.3 downgrade with no behavior change, on top of the v1.1.6 verification that already checked every import/method this integration calls exists at 2.2.0.
- 2026-08-15: v1.1.9 — added `CONNECT_TIMEOUT` (30s) around every `controller.connect()` call in `__init__.py` (initial setup and the 5-min health check), via `asyncio.timeout()`. Motivated by diagnosing a real report: the cloud push server (a fixed IP separate from the `user.intesishome.com` login API) was unreachable — TCP connects to it timed out while the login API and general internet both worked fine, pointing to an outage on IntesisHome's push-server side, not this integration or the network. `pyintesishome`'s own HTTP/socket calls have no timeout of their own (relies on aiohttp's ~5 min default at best), so a stalled cloud endpoint could make every retry ride out a long stall; this bounds it so retries fail fast into `ConfigEntryNotReady` / the debug log instead. Does not fix external outages, only how fast this integration detects and retries them.
- 2026-08-15: v1.1.8 — added `binary_sensor.py` (problem/alarm, filter clean, connectivity) and `button.py` (reset filter, writes raw UID 184 via `_set_value` since pyintesishome has no COMMAND_MAP entry for it), plus `error_code` (disabled by default) and `filter_due_hours` sensors in `sensor.py`. All read data pyintesishome already exposes per-device (`alarm_status`/`filter_clean`/`filter_due_hours`/`error_code`, UIDs 14/183/184/15) via `get_device_property()`, so no new controller wiring was needed. Prompted by comparing against jnimmo/hass-intesishome, which already had these platforms. Also downgraded `pyintesishome` 2.2.0 → 2.0.3: confirmed `const.py` and `intesishome.py` (the cloud class) are byte-identical between the two versions — 2.1.0/2.2.0's only changes are `last_successful_update` staleness tracking on `IntesisHomeLocal`, unused by this integration's cloud path — and confirmed on GitHub (jnimmo/pyIntesisHome, the upstream repo for this PyPI package) that v2.0.3 itself only fixed an IntesisBox callback bug, so the new entities above work unchanged at this pinned version.
- 2026-08-15: v1.1.7 — added a cloud-service selector (IntesisHome, airconwithme, or anywAiR) to the setup and reauth flows. The selected service is now passed to pyintesishome instead of always targeting the IntesisHome endpoint. Existing entries default to IntesisHome until reauthenticated.
- 2026-08-15: v1.1.6 — bumped `pyintesishome` 2.0.2 → 2.2.0. Verified (installed in a scratch venv) every import/method this integration uses (`IntesisHome`, `IHAuthenticationError`, `IHConnectionError`, all getter/setter calls) is still present. 2.1.0/2.2.0's changes (staleness detection, `IHConnectionError`/`IHAuthenticationError` raised instead of swallowed, backoff polling) are scoped to `IntesisHomeLocal` (local IntesisBox) — upstream release notes state cloud (`IntesisHome`) behavior is unchanged, so this does not affect the reconnect/health-check design described below.
- 2026-08-06: v1.1.5 — fixed HVAC mode (and swing/fan/preset/target-temp feature) list getting stuck at "off only" — `climate.py` computed `_attr_hvac_modes` etc. once in `IntesisAC.__init__`, but `controller.connect()` only waits for cloud login, not the full initial device-capability push that streams in afterward (config_mode_map/config_operating_mode UIDs). If the entity was constructed before that stream finished, modes never appeared. Extracted the logic into `_refresh_capabilities()`, called from both `__init__` and every `async_update()`, so capabilities self-heal on the next push instead of freezing at creation time. Checked HA core 2026.7/2026.8 changelogs first — no actual climate-entity breaking change there; this was a pre-existing race that just needed a fix.
- 2026-07-19: v1.1.4 — added connection health check with runtime reauth; added Wi-Fi RSSI diagnostic sensor; exposed rssi/run_hours as climate attributes; min setpoint logic reworked (`MIN_TEMP_LIMIT` cap, kept at 18 °C after briefly trying 16); fixed falsy-temperature skip in `async_set_temperature`; guarded unknown preset modes; `PARALLEL_UPDATES = 0`; controller stopped if platform setup fails. (v1.1.3 with the 16 °C cap was never released.)
- 2026-07-19 and earlier: v1.1.x — initial config flow, climate + sensor platforms, reauth flow, mode-based icons.
