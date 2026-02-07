# Grafana Integration Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           IoT Sensor Network                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │ BME680   │  │ MMC5983  │  │ VEML7700 │  │STHS34PF80│  ... other sensors │
│  │ (Temp,   │  │ (Magnet) │  │ (Light)  │  │(Presence)│                    │
│  │  Air Q)  │  │          │  │          │  │          │                    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                    │
│       │             │              │             │                          │
│       └─────────────┴──────────────┴─────────────┘                          │
│                             │                                                │
│                             ▼                                                │
│                    ┌─────────────────┐                                       │
│                    │  MQTT Broker    │                                       │
│                    │  (Mosquitto)    │                                       │
│                    │  localhost:1883 │                                       │
│                    │  Topic: iot_logger                                      │
│                    └─────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               │ JSON Messages
                               │ (1/sec typical)
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Data Processing Layer                               │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                         Telegraf                                      │  │
│   │  ┌──────────────────┐                                                │  │
│   │  │  MQTT Consumer   │  Subscribes to iot_logger topic               │  │
│   │  │  Plugin          │  Parses JSON messages                         │  │
│   │  └────────┬─────────┘                                                │  │
│   │           │                                                           │  │
│   │           ▼                                                           │  │
│   │  ┌──────────────────────────────────────────────────────────────┐   │  │
│   │  │           Starlark Processor (Custom Logic)                   │   │  │
│   │  │                                                                │   │  │
│   │  │  ┌──────────────────────────────────────────────────────────┐ │   │  │
│   │  │  │  Air Quality Calculation (BME680)                        │ │   │  │
│   │  │  │  • 50-sample gas resistance baseline                     │ │   │  │
│   │  │  │  • Humidity-weighted scoring (40% ideal)                 │ │   │  │
│   │  │  │  • Output: 0-100 score (higher = better)                 │ │   │  │
│   │  │  └──────────────────────────────────────────────────────────┘ │   │  │
│   │  │                                                                │   │  │
│   │  │  ┌──────────────────────────────────────────────────────────┐ │   │  │
│   │  │  │  Magnet Detection (MMC5983)                              │ │   │  │
│   │  │  │  • Calculate 3D magnitude (sqrt(x²+y²+z²))               │ │   │  │
│   │  │  │  • 20-sample moving average baseline                     │ │   │  │
│   │  │  │  • Trigger: magnitude > 2x baseline                      │ │   │  │
│   │  │  └──────────────────────────────────────────────────────────┘ │   │  │
│   │  │                                                                │   │  │
│   │  │  ┌──────────────────────────────────────────────────────────┐ │   │  │
│   │  │  │  Person Detection (STHS34PF80)                           │ │   │  │
│   │  │  │  • Presence >= 1000 OR Motion > 0                        │ │   │  │
│   │  │  │  • Output: Binary flag (0/1)                             │ │   │  │
│   │  │  └──────────────────────────────────────────────────────────┘ │   │  │
│   │  └──────────────────────────────────────────────────────────────┘   │  │
│   │           │                                                           │  │
│   │           ▼                                                           │  │
│   │  ┌──────────────────┐                                                │  │
│   │  │  InfluxDB Output │  Writes to sensor_data bucket                 │  │
│   │  └──────────────────┘                                                │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               │ Time-series data
                               │ (influx line protocol)
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Storage Layer                                       │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                        InfluxDB 2.x                                   │  │
│   │  Organization: sensors                                                │  │
│   │  Bucket: sensor_data                                                  │  │
│   │                                                                        │  │
│   │  Data Storage:                                                         │  │
│   │  • Compressed time-series (~5 MB/day for 1 reading/sec)              │  │
│   │  • Automatic downsampling for old data                               │  │
│   │  • Retention policies (default: unlimited)                           │  │
│   │                                                                        │  │
│   │  API: http://localhost:8086                                           │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               │ Flux queries
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Visualization Layer                                    │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │                         Grafana                                       │  │
│   │  http://localhost:3000                                                │  │
│   │                                                                        │  │
│   │  Dashboard Panels:                                                     │  │
│   │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │  │
│   │  │  Temperature   │  │  Air Quality   │  │  Humidity      │          │  │
│   │  │  (Time Series) │  │  (Gauge 0-100) │  │  (Time Series) │          │  │
│   │  └────────────────┘  └────────────────┘  └────────────────┘          │  │
│   │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │  │
│   │  │  Mag Field     │  │  Light Level   │  │  Magnet Alert  │          │  │
│   │  │  (with baseline)│  │  (Lux)         │  │  (Stat: 0/1)   │          │  │
│   │  └────────────────┘  └────────────────┘  └────────────────┘          │  │
│   │  ┌────────────────┐  ┌────────────────┐                              │  │
│   │  │  Air Quality   │  │  Person        │                              │  │
│   │  │  (History)     │  │  (Stat: 0/1)   │                              │  │
│   │  └────────────────┘  └────────────────┘                              │  │
│   │                                                                        │  │
│   │  Alerts:                                                               │  │
│   │  • Low air quality (< 30)                                             │  │
│   │  • Magnet detection                                                   │  │
│   │  • Temperature thresholds                                             │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Details

### 1. MQTT Message Format (Input)

```json
{
  "BME68x": {
    "Humidity": 38.06989,
    "TemperatureC": 21.01744,
    "Pressure": 100407.8,
    "Gas Resistance": 91647.23
  },
  "MMC5983": {
    "X Field (Gauss)": -0.382629,
    "Y Field (Gauss)": -0.799194,
    "Z Field (Gauss)": -0.648071,
    "Temperature (C)": 16
  },
  "VEML7700": {
    "Lux": 150.4512
  },
  "STHS34PF80": {
    "Presence (cm^-1)": 3,
    "Motion (LSB)": -28
  }
}
```

### 2. Telegraf Processing (Transformation)

**Input Fields → Processed Output:**

| Raw MQTT Field | Processing | Output Field |
|----------------|------------|--------------|
| `BME68x_Gas Resistance` + `BME68x_Humidity` | Air quality algorithm | `air_quality_score` (0-100) |
| `BME68x_Gas Resistance` | 50-sample average | `gas_baseline` |
| `MMC5983_X/Y/Z Field` | sqrt(x²+y²+z²) | `mag_magnitude` |
| `mag_magnitude` | 20-sample average | `mag_baseline` |
| `mag_magnitude` vs `mag_baseline` | magnitude > 2x baseline | `magnet_detected` (0/1) |
| `STHS34PF80_Presence` + `Motion` | presence≥1000 OR motion>0 | `person_detected` (0/1) |

### 3. InfluxDB Storage (Time-Series)

**Measurement**: `sensors`

**Fields** (examples):
- `BME68x_TemperatureC`: 21.01744
- `BME68x_Humidity`: 38.06989
- `air_quality_score`: 72.5
- `gas_baseline`: 91000.0
- `mag_magnitude`: 1.0234
- `mag_baseline`: 0.9512
- `magnet_detected`: 0
- `person_detected`: 1

**Tags**: (optional)
- `sensor_type`: "BME68x", "MMC5983", etc.
- `location`: "office", "bedroom", etc.

### 4. Grafana Queries (Visualization)

**Example 1: Temperature Time Series**
```flux
from(bucket: "sensor_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_field"] == "BME68x_TemperatureC")
  |> aggregateWindow(every: 1m, fn: mean)
```

**Example 2: Current Air Quality**
```flux
from(bucket: "sensor_data")
  |> range(start: -5s)
  |> filter(fn: (r) => r["_field"] == "air_quality_score")
  |> last()
```

**Example 3: Magnet Detection Events (Last 24h)**
```flux
from(bucket: "sensor_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_field"] == "magnet_detected")
  |> filter(fn: (r) => r["_value"] == 1)
  |> aggregateWindow(every: 1m, fn: sum)
```

## Resource Usage on Raspberry Pi

```
┌─────────────────────────────────────────────────┐
│         Component Resource Breakdown             │
├─────────────────┬────────┬──────┬───────────────┤
│ Component       │ RAM    │ CPU  │ Disk          │
├─────────────────┼────────┼──────┼───────────────┤
│ MQTT Broker     │   5 MB │  <1% │   ~10 MB      │
│ Telegraf        │  50 MB │ 2-5% │   ~50 MB      │
│ InfluxDB        │ 200 MB │ 5-10%│ ~500 MB+data  │
│ Grafana         │ 150 MB │ 2-5% │  ~100 MB      │
├─────────────────┼────────┼──────┼───────────────┤
│ TOTAL           │ 400 MB │ 10-20%│ ~660 MB+data │
└─────────────────┴────────┴──────┴───────────────┘

Minimum Hardware: Raspberry Pi 3B+ (1GB RAM)
Recommended: Raspberry Pi 4 (2GB+ RAM)
```

## Key Design Decisions

### ✅ Why Telegraf?

- **Native MQTT support**: No custom code needed for MQTT consumption
- **Starlark scripting**: Stateful processing (baselines, moving averages)
- **Battle-tested**: Used in production by thousands of organizations
- **Lightweight**: Only ~50MB RAM, 2-5% CPU
- **Systemd integration**: Auto-restart, logging built-in

### ✅ Why InfluxDB?

- **Time-series optimized**: Compression, downsampling, retention policies
- **Flux query language**: Powerful aggregations and transformations
- **Native Grafana support**: Best integration, fastest queries
- **Historical data**: Unlimited storage (vs. MQTT direct connection)
- **Resource efficient**: ~200MB RAM on Raspberry Pi

### ✅ Why Grafana?

- **Industry standard**: Professional dashboards, alerting, user management
- **InfluxDB integration**: Excellent Flux query support
- **Alert channels**: Email, Slack, webhooks, etc.
- **Dashboard sharing**: Import/export JSON, templating
- **Mobile support**: Responsive dashboards

## Alternative Approaches (Not Chosen)

### ❌ Direct MQTT → Grafana
**Problem**: No historical data, limited transformations, no alerting

### ❌ Custom Python Bridge
**Problem**: Custom maintenance burden, need to manage service reliability

### ❌ MQTT Re-broadcast
**Problem**: Adds complexity without clear benefits over Telegraf

## Deployment Architecture

```
Production Setup:
┌─────────────────────────────────────────────────┐
│        Raspberry Pi (Single Device)              │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Mosquitto (MQTT Broker)                 │   │
│  │  systemd service: mosquitto.service      │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Telegraf (Data Processor)               │   │
│  │  systemd service: telegraf.service       │   │
│  │  Config: /etc/telegraf/telegraf.conf     │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  InfluxDB (Time-Series DB)               │   │
│  │  systemd service: influxdb.service       │   │
│  │  Data: /var/lib/influxdb                 │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  Grafana (Visualization)                 │   │
│  │  systemd service: grafana-server.service │   │
│  │  Web UI: http://localhost:3000           │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

All services run as systemd units with automatic restart on failure.

## See Also

- **Setup Instructions**: `examples/grafana/README.md`
- **Architecture Analysis**: `GRAFANA_INTEGRATION_STRATEGY.md`
- **MQTT Data Format**: `MQTT_SENSOR_PLUGIN.md`
- **Telegraf Config**: `examples/grafana/telegraf.conf`
- **Dashboard JSON**: `examples/grafana/dashboard.json`
