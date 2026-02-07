# SSD1305 OLED Dashboard - AI Agent Instructions

## Project Overview
This is an extended fork of Adafruit's CircuitPython SSD1305 OLED driver, transformed into a flexible IoT sensor dashboard platform with plugin architecture, web simulation, MQTT integration, and OLED burn-in prevention.

**Tech stack:** Python 3.8+, ruff (linter/formatter), pytest (testing), REUSE (license compliance)

**Core modules:**
- `adafruit_ssd1305.py` - Low-level framebuffer driver (original Adafruit code, do not modify)
- `sensor_plugins/` - Hot-pluggable sensor plugin system (10 plugins)
- `display_timeout.py` - OLED burn-in prevention with keyboard activity detection
- `terminal_streamer.py` - Callback-based terminal output capture and broadcast
- `examples/` - Stats display, web simulator, MQTT examples

## Plugin System Architecture

**All sensor plugins extend `sensor_plugins/base.py:SensorPlugin`:**
```python
class MyPlugin(SensorPlugin):
    def _initialize_hardware(self):
        # Initialize sensor, raise exception if unavailable
        return sensor_object
    
    def _read_sensor_data(self) -> Dict[str, Any]:
        # Return {"field": value, ...}
        return {"temperature": self.sensor_instance.temperature}
    
    @property
    def requires_background_updates(self) -> bool:
        # Return True if sensor needs continuous reads (e.g., BME680 burn-in)
        return False
```

**Key patterns:**
- Plugins auto-register via `sensor_plugins/__init__.py`
- Hot-plug support via `check_availability()` (default 5s interval)
- Graceful degradation: `read()` returns fallback data if hardware unavailable
- Thread-safe: Use locks for shared state (see BME680Plugin cache)

**Available plugins:** TMP117, BME680, VEML7700, STHS34PF80, MMC5983, CPULoad, MemoryUsage, IPAddress, Keyboard, MQTT

## Development Workflows

**Install dependencies:**
```bash
pip install -r requirements.txt              # Core: Blinka, busdevice, framebuf
pip install -r optional_requirements.txt     # Optional: PIL, paho-mqtt, websockets, pynput, evdev, rich, textual
```

**Lint and format:**
```bash
ruff check .                                  # Lint (rules configured in ruff.toml)
ruff format --check .                         # Check formatting (line-length 100, LF endings)
ruff check --fix .                            # Auto-fix lint issues
ruff format .                                 # Auto-format code
```

**Run tests:**
```bash
python -m pytest tests/test_sensor_plugin.py  # Plugin tests with mocked hardware
```

**Run examples:**
```bash
python examples/ssd1305_stats.py --blank-timeout 10 --debug  # Stats display with burn-in prevention
python examples/ssd1305_web_simulator.py --use-mocks --enable-websocket  # Web simulator
python examples/mqtt_sensor_example.py --broker localhost --port 1883  # MQTT example
```

**Test with static MQTT messages:**
- Use `examples/test_mmc5983_mqtt.py` pattern: hardcoded JSON payloads
- MQTT plugin extracts sensor data from JSON (see `sensor_plugins/mqtt_plugin.py:_read_sensor_data`)

## Coding Conventions

**Formatting (enforced by ruff):**
- Target Python 3.8+ (`target-version = "py38"` in `ruff.toml`)
- Line length: 100 characters
- Line endings: LF
- Pre-commit hooks run ruff format, ruff lint, and REUSE license checks

**REUSE license compliance:**
- All files must have SPDX license headers (checked by pre-commit and CI)
- Use `# SPDX-FileCopyrightText:` and `# SPDX-License-Identifier:` comments
- See existing files for examples of the required header format

**Dependencies:**
- Keep `requirements.txt` (core) and `optional_requirements.txt` (optional) up to date
- Install only via requirements files, not direct pip commands in scripts

**Script parameters:**
- Always use `argparse` for configuration (ports, hostnames, timeouts)
- Default to sane values: `localhost`, standard ports (1883 for MQTT, 8000 for HTTP)
- Example: `parser.add_argument("--broker", default="localhost", help="MQTT broker hostname")`

**Testing:**
- Write tests for all new plugins and features
- Use `unittest.mock.patch.dict` to mock `sys.modules` for optional dependencies (see `tests/test_sensor_plugin.py`)
- Test scripts with static data (no hardware dependencies)

**Error handling:**
- Plugins: Catch exceptions in `_initialize_hardware()`, set `self.available = False`
- Missing dependencies: Show clear error messages with pip install instructions (see `examples/mqtt_sensor_example_rich.py:32-43`)

## Boundaries

**Do not modify:**
- `adafruit_ssd1305.py` - Original Adafruit driver; upstream changes only
- `.github/workflows/` - CI workflows managed separately
- `LICENSES/` - License files managed by REUSE tool

## Key Files & Patterns

**Plugin examples:**
- `sensor_plugins/tmp117_plugin.py` - Simple temperature sensor
- `sensor_plugins/bme680_plugin.py` - Complex with burn-in cache and background updates
- `sensor_plugins/mmc5983_plugin.py` - Magnetometer with magnet detection via `sensor_plugins/magnet_detector.py`
- `sensor_plugins/mqtt_plugin.py` - Virtual sensor reading from MQTT JSON messages

**Display timeout:**
- `display_timeout.py` - Reusable module with 5 keyboard detection methods (auto/pynput/evdev/file/stdin)
- Pattern: `timeout_manager.should_display_be_active()` in display loop
- BME680 requires background updates even when display blanked (check `plugin.requires_background_updates`)

**Web simulator:**
- `examples/ssd1305_web_simulator.py` - HTTP server + optional WebSocket push
- Performance metrics documented in `PERFORMANCE.md`
- Dynamic refresh rate, client-side image scaling, background sensor caching

**Documentation:**
- `examples/README.md` - Comprehensive example usage guide
- `MQTT_SENSOR_PLUGIN.md` - MQTT integration details
- `IMPLEMENTATION_SUMMARY.md` - Architecture overview
- `PERFORMANCE.md` - Optimization strategies
