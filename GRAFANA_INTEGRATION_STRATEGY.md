# Grafana Integration Strategy for MQTT Sensor Dashboard

## Executive Summary

This document evaluates multiple architectural approaches for integrating the existing MQTT sensor system with Grafana for data visualization and monitoring on a Raspberry Pi.

**Recommended Solution**: **Option 3 - Telegraf + InfluxDB + Grafana Stack** (Best balance of simplicity, features, and maintenance)

## Current Architecture

### Existing System Components

1. **MQTT Broker** (running on Raspberry Pi)
   - Receives sensor data from IoT devices
   - Topic: `iot_logger` (default)
   - Port: 1883

2. **Sensor Data Sources**
   - BME680: Temperature, humidity, pressure, gas resistance with custom air quality calculation
   - MMC5983: 3-axis magnetometer with custom magnet detection algorithm
   - VEML7700: Light sensor (lux)
   - TMP117: Temperature sensor
   - STHS34PF80: Presence/motion detection
   - MAX17048: Battery monitoring
   - System Info: WiFi stats

3. **Custom Processing Logic**
   - **Air Quality Algorithm** (BME680):
     - 5-minute burn-in period
     - Rolling 50-sample baseline calculation
     - Humidity-weighted scoring (0-100 scale)
   - **Magnet Detection** (MMC5983):
     - 20-sample moving average baseline
     - 2x threshold detection
     - Direction-independent 3D magnitude calculation

4. **MQTT Data Format** (JSON):
```json
{
  "BME68x": {
    "Humidity": 38.06989,
    "TemperatureC": 21.01744,
    "Pressure": 100407.8,
    "Gas Resistance": 91647.23,
    "Sensor Status": 176
  },
  "MMC5983": {
    "X Field (Gauss)": -0.382629,
    "Y Field (Gauss)": -0.799194,
    "Z Field (Gauss)": -0.648071,
    "Temperature (C)": 16
  },
  "VEML7700": {"Lux": 150.4512},
  "TMP117": {"Temperature (C)": 21.03906},
  "STHS34PF80": {
    "Presence (cm^-1)": 3,
    "Motion (LSB)": -28,
    "Temperature (C)": 0
  }
}
```

## Architecture Options Analysis

### Option 1: Direct MQTT to Grafana (MQTT Datasource Plugin)

**Description**: Use Grafana's native MQTT datasource plugin to subscribe directly to MQTT topics.

**Pros**:
- ✅ Simplest setup - no intermediate services
- ✅ Near real-time visualization
- ✅ No additional infrastructure
- ✅ Direct connection minimizes latency

**Cons**:
- ❌ **No data persistence** - can't view historical data
- ❌ **Limited transformation** - can't apply custom air quality/magnet detection logic
- ❌ **No alerting** - limited notification capabilities
- ❌ **Single point of failure** - if Grafana restarts, data is lost
- ❌ Complex JSON parsing in Grafana queries

**Verdict**: ❌ **Not Recommended** - Lack of historical data and custom processing makes this unsuitable for our use case.

---

### Option 2: Custom Python Bridge Service

**Description**: Build a custom Python service that subscribes to MQTT, processes data, and exposes Prometheus metrics or writes to InfluxDB.

**Architecture**:
```
MQTT Broker → Python Bridge → Prometheus/InfluxDB → Grafana
                ↓
            Custom Processing
            (Air Quality, Magnet Detection)
```

**Implementation Sketch**:
```python
# mqtt_to_influx_bridge.py
from influxdb_client import InfluxDBClient, Point
from sensor_plugins import MQTTPlugin

mqtt = MQTTPlugin(broker_host="localhost", topic="iot_logger")
influx = InfluxDBClient(url="http://localhost:8086", token="...", org="sensors")

while True:
    data = mqtt.read()
    
    # Write raw sensor data
    point = Point("sensors")
    if data["temperature"] != "n/a":
        point.field("bme680_temperature", data["temperature"])
    if data["air_quality"] != "n/a":
        point.field("air_quality_score", data["air_quality"])
    
    influx.write_api().write(bucket="sensors", record=point)
    time.sleep(1)
```

**Pros**:
- ✅ **Full control** over processing logic
- ✅ Can reuse existing MQTTPlugin code
- ✅ Custom air quality and magnet detection preserved
- ✅ Flexible data transformation

**Cons**:
- ❌ **Custom maintenance burden** - you own the bridge code
- ❌ Need to handle service reliability (systemd, restarts, logging)
- ❌ More complex than off-the-shelf solutions
- ❌ Need to manage InfluxDB/Prometheus separately

**Verdict**: ⚠️ **Viable but not ideal** - Good if you need maximum control, but adds maintenance overhead.

---

### Option 3: Telegraf + InfluxDB + Grafana (TIG Stack) ⭐ **RECOMMENDED**

**Description**: Use Telegraf to collect MQTT data, process it, and store in InfluxDB for Grafana visualization.

**Architecture**:
```
MQTT Broker → Telegraf → InfluxDB → Grafana
              ↓
          Starlark/Processor
          (Custom Processing)
```

**Why This Works**:
- Telegraf has native MQTT consumer plugin
- Supports Starlark scripting for custom transformations
- Can calculate air quality and magnet detection in Telegraf
- InfluxDB provides time-series storage and historical data
- Grafana has excellent InfluxDB support

**Telegraf Configuration** (`telegraf.conf`):
```toml
# Input: MQTT Consumer
[[inputs.mqtt_consumer]]
  servers = ["tcp://localhost:1883"]
  topics = ["iot_logger"]
  data_format = "json"
  json_name_key = "sensor_type"
  tag_keys = ["sensor_type"]

# Processor: Calculate Air Quality (Starlark)
[[processors.starlark]]
  source = '''
def apply(metric):
    # Extract BME680 data
    if "BME68x_Gas_Resistance" in metric.fields:
        gas = metric.fields["BME68x_Gas_Resistance"]
        hum = metric.fields.get("BME68x_Humidity", 40)
        
        # Simplified air quality calculation
        # (Full implementation would track baseline)
        gas_score = min(100, (gas / 1000))
        hum_offset = abs(hum - 40)
        hum_score = max(0, 100 - hum_offset * 2)
        
        metric.fields["air_quality_score"] = (gas_score * 0.75 + hum_score * 0.25)
    
    # Calculate magnetic field magnitude
    if all(k in metric.fields for k in ["MMC5983_X_Field", "MMC5983_Y_Field", "MMC5983_Z_Field"]):
        x = metric.fields["MMC5983_X_Field"]
        y = metric.fields["MMC5983_Y_Field"]
        z = metric.fields["MMC5983_Z_Field"]
        
        magnitude = (x**2 + y**2 + z**2)**0.5
        metric.fields["mag_magnitude"] = magnitude
    
    return metric
'''

# Output: InfluxDB
[[outputs.influxdb_v2]]
  urls = ["http://localhost:8086"]
  token = "$INFLUX_TOKEN"
  organization = "sensors"
  bucket = "sensor_data"
```

**Installation Steps**:
```bash
# 1. Install InfluxDB 2.x
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.4-arm64.deb
sudo dpkg -i influxdb2-2.7.4-arm64.deb
sudo systemctl start influxdb

# 2. Install Telegraf
wget https://dl.influxdata.com/telegraf/releases/telegraf_1.29.0-1_arm64.deb
sudo dpkg -i telegraf_1.29.0-1_arm64.deb

# 3. Configure Telegraf (see above)
sudo nano /etc/telegraf/telegraf.conf
sudo systemctl restart telegraf

# 4. Grafana already installed - just add InfluxDB datasource
```

**Pros**:
- ✅ **Industry standard** - proven, well-maintained
- ✅ **Time-series storage** - unlimited historical data
- ✅ **Custom processing** - Starlark scripting for air quality/magnet detection
- ✅ **Easy deployment** - systemd services, auto-restart
- ✅ **Great Grafana integration** - native InfluxDB support
- ✅ **Scalable** - can handle thousands of metrics
- ✅ **Alerting** - InfluxDB + Grafana alerts out of the box
- ✅ **Downsampling** - can aggregate old data to save space

**Cons**:
- ⚠️ Need to install InfluxDB (~150MB) and Telegraf (~50MB)
- ⚠️ Starlark processing is simpler than full Python (but sufficient)
- ⚠️ Requires learning Telegraf configuration syntax

**Verdict**: ✅ **RECOMMENDED** - Best balance of features, reliability, and maintenance.

---

### Option 4: Process & Re-broadcast via MQTT

**Description**: Create a service that reads raw MQTT, processes it, and publishes processed metrics to a new MQTT topic that Grafana (via MQTT plugin) or Telegraf can consume.

**Architecture**:
```
MQTT Broker (raw) → Python Processor → MQTT Broker (processed) → Grafana/Telegraf
                    ↓
                Air Quality, Magnet Detection
```

**Python Implementation**:
```python
# mqtt_processor.py
import paho.mqtt.client as mqtt
from sensor_plugins import MQTTPlugin

# Subscribe to raw data
mqtt_in = MQTTPlugin(broker_host="localhost", topic="iot_logger")

# Publish processed data
mqtt_out = mqtt.Client()
mqtt_out.connect("localhost", 1883)

while True:
    data = mqtt_in.read()
    
    # Publish individual metrics
    if data["air_quality"] != "n/a":
        mqtt_out.publish("sensors/air_quality", data["air_quality"])
    if data["magnet_detected"] != "n/a":
        mqtt_out.publish("sensors/magnet_detected", 1 if data["magnet_detected"] else 0)
    
    time.sleep(1)
```

**Pros**:
- ✅ Reuses existing MQTT infrastructure
- ✅ Can leverage existing MQTTPlugin logic
- ✅ Decoupled - processor doesn't need to know about storage

**Cons**:
- ❌ Still need time-series database for historical data
- ❌ Adds complexity (another service to manage)
- ❌ Duplicates data in MQTT (raw + processed)
- ❌ Not fundamentally better than Option 2 or 3

**Verdict**: ⚠️ **Not Recommended** - Adds complexity without clear benefits over Telegraf.

---

## Recommended Implementation: Telegraf + InfluxDB + Grafana

### Why This Is The Best Choice

1. **Preserves Custom Logic**: Telegraf's Starlark processor can implement air quality calculation and magnet detection
2. **Production Ready**: Battle-tested, used by thousands of organizations
3. **Low Maintenance**: Managed by systemd, automatic restarts, logging built-in
4. **Historical Data**: InfluxDB stores unlimited time-series data with compression
5. **Grafana Native**: InfluxDB is one of Grafana's best-supported datasources
6. **Alerting**: Built-in alert notifications (email, Slack, etc.)
7. **Resource Efficient**: Lightweight enough for Raspberry Pi

### Implementation Plan

#### Phase 1: Basic Setup (30 minutes)

1. **Install InfluxDB 2.x**
```bash
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.4-arm64.deb
sudo dpkg -i influxdb2-2.7.4-arm64.deb
sudo systemctl enable influxdb
sudo systemctl start influxdb

# Setup via web UI: http://localhost:8086
# Create organization "sensors" and bucket "sensor_data"
# Save the API token
```

2. **Install Telegraf**
```bash
wget https://dl.influxdata.com/telegraf/releases/telegraf_1.29.0-1_arm64.deb
sudo dpkg -i telegraf_1.29.0-1_arm64.deb
sudo systemctl enable telegraf
```

3. **Configure Telegraf** (minimal config to start)
```toml
# /etc/telegraf/telegraf.conf

[agent]
  interval = "1s"
  flush_interval = "1s"

[[inputs.mqtt_consumer]]
  servers = ["tcp://localhost:1883"]
  topics = ["iot_logger"]
  data_format = "json_v2"
  
  [[inputs.mqtt_consumer.json_v2]]
    [[inputs.mqtt_consumer.json_v2.object]]
      path = "BME68x"
      tags = ["sensor_type"]
      
    [[inputs.mqtt_consumer.json_v2.object]]
      path = "VEML7700"
      tags = ["sensor_type"]
      
    [[inputs.mqtt_consumer.json_v2.object]]
      path = "MMC5983"
      tags = ["sensor_type"]

[[outputs.influxdb_v2]]
  urls = ["http://localhost:8086"]
  token = "$INFLUX_TOKEN"  # Replace with your token
  organization = "sensors"
  bucket = "sensor_data"
```

4. **Start Telegraf**
```bash
sudo systemctl start telegraf
sudo systemctl status telegraf  # Check it's running
```

#### Phase 2: Add Custom Processing (1 hour)

Create advanced Telegraf processors for air quality and magnet detection.

**File**: `/etc/telegraf/telegraf.d/custom_processing.conf`

```toml
# Air Quality Calculation
[[processors.starlark]]
  namepass = ["mqtt_consumer"]
  source = '''
# State management for baseline calculation
state = {
    "gas_samples": [],
    "gas_baseline": None,
    "mag_samples": [],
    "mag_baseline": None,
}

def apply(metric):
    # Air Quality Calculation
    if "BME68x_Gas_Resistance" in metric.fields and "BME68x_Humidity" in metric.fields:
        gas = metric.fields["BME68x_Gas_Resistance"]
        hum = metric.fields["BME68x_Humidity"]
        
        # Build baseline (simplified - keeps last 50 samples)
        state["gas_samples"].append(gas)
        if len(state["gas_samples"]) > 50:
            state["gas_samples"] = state["gas_samples"][-50:]
        
        if len(state["gas_samples"]) >= 10:
            state["gas_baseline"] = sum(state["gas_samples"]) / len(state["gas_samples"])
            
            # Calculate air quality score
            gas_offset = state["gas_baseline"] - gas
            hum_baseline = 40.0
            hum_offset = hum - hum_baseline
            
            # Humidity score
            if hum_offset > 0:
                hum_score = (100 - hum_baseline - hum_offset) / (100 - hum_baseline) * 25
            else:
                hum_score = (hum_baseline + hum_offset) / hum_baseline * 25
            
            # Gas score
            if gas_offset > 0 and state["gas_baseline"] > 0:
                gas_score = (gas / state["gas_baseline"]) * 75
            else:
                gas_score = 75
            
            metric.fields["air_quality_score"] = max(0, min(100, hum_score + gas_score))
            metric.fields["gas_baseline"] = state["gas_baseline"]
    
    # Magnet Detection
    if all(k in metric.fields for k in ["MMC5983_X_Field_Gauss", "MMC5983_Y_Field_Gauss", "MMC5983_Z_Field_Gauss"]):
        x = metric.fields["MMC5983_X_Field_Gauss"]
        y = metric.fields["MMC5983_Y_Field_Gauss"]
        z = metric.fields["MMC5983_Z_Field_Gauss"]
        
        # Calculate magnitude
        magnitude = (x*x + y*y + z*z)**0.5
        metric.fields["mag_magnitude"] = magnitude
        
        # Build baseline (20 samples)
        state["mag_samples"].append(magnitude)
        if len(state["mag_samples"]) > 20:
            state["mag_samples"] = state["mag_samples"][-20:]
        
        if len(state["mag_samples"]) >= 5:
            state["mag_baseline"] = sum(state["mag_samples"]) / len(state["mag_samples"])
            metric.fields["mag_baseline"] = state["mag_baseline"]
            
            # Detect magnet (2x threshold)
            if magnitude > state["mag_baseline"] * 2.0:
                metric.fields["magnet_detected"] = 1
            else:
                metric.fields["magnet_detected"] = 0
    
    return metric
'''
```

**Restart Telegraf**:
```bash
sudo systemctl restart telegraf
```

#### Phase 3: Configure Grafana Dashboard (30 minutes)

1. **Add InfluxDB Datasource** in Grafana
   - Settings → Data Sources → Add InfluxDB
   - Query Language: Flux
   - URL: http://localhost:8086
   - Organization: sensors
   - Token: (your InfluxDB token)
   - Default Bucket: sensor_data

2. **Create Dashboard Panels**

**Panel 1: Temperature Time Series**
```flux
from(bucket: "sensor_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_field"] == "BME68x_TemperatureC")
```

**Panel 2: Air Quality Score**
```flux
from(bucket: "sensor_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_field"] == "air_quality_score")
```

**Panel 3: Magnet Detection (Stat Panel)**
```flux
from(bucket: "sensor_data")
  |> range(start: -5s)
  |> filter(fn: (r) => r["_field"] == "magnet_detected")
  |> last()
```

**Panel 4: Magnetic Field Magnitude**
```flux
from(bucket: "sensor_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_field"] == "mag_magnitude")
```

3. **Set up Alerts**
   - Air quality < 30 → Alert
   - Magnet detected → Notification

### Alternative: Simplified Approach Without Custom Processing

If you don't need air quality calculation or magnet detection in Grafana, you can simplify:

**Option 3a: Telegraf + InfluxDB (No Custom Processing)**

Just store raw sensor values and do calculations in Grafana queries:

```toml
# Minimal telegraf.conf
[[inputs.mqtt_consumer]]
  servers = ["tcp://localhost:1883"]
  topics = ["iot_logger"]
  data_format = "json"

[[outputs.influxdb_v2]]
  urls = ["http://localhost:8086"]
  token = "$INFLUX_TOKEN"
  organization = "sensors"
  bucket = "sensor_data"
```

**Grafana Calculation Example** (for magnetic magnitude):
```flux
from(bucket: "sensor_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "mqtt_consumer")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> map(fn: (r) => ({
      _time: r._time,
      _value: sqrt(r.MMC5983_X_Field * r.MMC5983_X_Field + 
                   r.MMC5983_Y_Field * r.MMC5983_Y_Field + 
                   r.MMC5983_Z_Field * r.MMC5983_Z_Field)
  }))
```

**Pros**:
- ✅ Simpler Telegraf config
- ✅ No Starlark scripting needed
- ✅ Calculations in Grafana (easier to debug/modify)

**Cons**:
- ❌ Can't maintain stateful baselines for air quality
- ❌ More complex Grafana queries
- ❌ Higher query load on InfluxDB

## Resource Requirements

### Raspberry Pi Compatibility

| Component | RAM Usage | Disk Usage | CPU Usage |
|-----------|-----------|------------|-----------|
| MQTT Broker (Mosquitto) | ~5 MB | ~10 MB | <1% |
| Telegraf | ~50 MB | ~50 MB | 2-5% |
| InfluxDB 2.x | ~200 MB | ~500 MB + data | 5-10% |
| Grafana | ~150 MB | ~100 MB | 2-5% (idle) |
| **Total** | **~400 MB** | **~660 MB + data** | **10-20%** |

**Verdict**: ✅ Should run fine on Raspberry Pi 3B+ or newer (1GB+ RAM)

### Disk Space Management

InfluxDB retention policies to manage disk space:

```flux
// Delete data older than 30 days
option task = {name: "downsample-old-data", every: 1h}

from(bucket: "sensor_data")
  |> range(start: -30d, stop: -7d)
  |> aggregateWindow(every: 5m, fn: mean)
  |> to(bucket: "sensor_data_downsampled")

// Keep only downsampled data older than 7 days
```

## Deployment Checklist

- [ ] Install InfluxDB and complete initial setup
- [ ] Create organization "sensors" and bucket "sensor_data"
- [ ] Save InfluxDB API token securely
- [ ] Install Telegraf
- [ ] Configure Telegraf MQTT consumer
- [ ] Test Telegraf connection to MQTT broker
- [ ] Verify data flowing into InfluxDB (check web UI)
- [ ] Add InfluxDB datasource to Grafana
- [ ] Create initial dashboard with temperature panel
- [ ] Add air quality panel
- [ ] Add magnet detection panel
- [ ] Set up alert rules
- [ ] Configure systemd auto-restart for all services
- [ ] Test failover scenarios (restart services)
- [ ] Document for future maintenance

## Troubleshooting

### Telegraf not receiving MQTT messages

```bash
# Check Telegraf logs
sudo journalctl -u telegraf -f

# Test MQTT manually
mosquitto_sub -h localhost -t iot_logger -v

# Verify Telegraf can connect to MQTT
sudo telegraf --test --config /etc/telegraf/telegraf.conf
```

### No data in InfluxDB

```bash
# Check InfluxDB logs
sudo journalctl -u influxdb -f

# Query InfluxDB CLI
influx query 'from(bucket:"sensor_data") |> range(start: -1h) |> limit(n:10)'
```

### Starlark processor errors

```bash
# Enable debug logging in Telegraf
[agent]
  debug = true

sudo systemctl restart telegraf
sudo journalctl -u telegraf -f | grep starlark
```

## Conclusion

**Recommendation**: Use **Telegraf + InfluxDB + Grafana** (Option 3)

This provides:
- ✅ Production-ready, well-maintained stack
- ✅ Preserves custom air quality and magnet detection logic
- ✅ Historical data storage with time-series optimization
- ✅ Professional dashboards and alerting
- ✅ Low maintenance overhead
- ✅ Suitable for Raspberry Pi

**Next Steps**:
1. Follow Phase 1 implementation (basic setup)
2. Verify data flows into InfluxDB
3. Create initial Grafana dashboards
4. Add custom processing (Phase 2) if needed
5. Set up alerts for critical thresholds

**Estimated Time**: 2-3 hours for complete setup

## References

- [Telegraf MQTT Consumer Plugin](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/mqtt_consumer)
- [Telegraf Starlark Processor](https://github.com/influxdata/telegraf/tree/master/plugins/processors/starlark)
- [InfluxDB on Raspberry Pi](https://docs.influxdata.com/influxdb/v2.7/install/?t=Raspberry+Pi)
- [Grafana Installation](https://grafana.com/tutorials/install-grafana-on-raspberry-pi/)
- Existing MQTT documentation: `MQTT_SENSOR_PLUGIN.md`
