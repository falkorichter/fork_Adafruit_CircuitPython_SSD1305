# Grafana Integration for MQTT Sensor Dashboard

This directory contains everything you need to integrate your MQTT sensor system with Grafana for professional data visualization and monitoring.

## 📋 Overview

This integration uses the **TIG Stack** (Telegraf + InfluxDB + Grafana):

```
IoT Devices → MQTT Broker → Telegraf → InfluxDB → Grafana
                              ↓
                        Custom Processing
                    (Air Quality, Magnet Detection)
```

**Features:**
- ✅ Historical data storage (unlimited time-series data)
- ✅ Custom air quality calculation (BME680 burn-in & scoring)
- ✅ Automatic magnet detection (MMC5983 baseline tracking)
- ✅ Person presence detection (STHS34PF80)
- ✅ Professional dashboards with alerts
- ✅ Production-ready, low maintenance
- ✅ Runs on Raspberry Pi

## 🚀 Quick Start

### Prerequisites

1. **Raspberry Pi** with Raspberry Pi OS (or any Debian-based Linux)
2. **MQTT Broker** (mosquitto) already running
3. **Grafana** already installed ([installation guide](https://grafana.com/tutorials/install-grafana-on-raspberry-pi/))
4. IoT devices publishing sensor data to MQTT topic `iot_logger`

### Installation (Automated)

```bash
cd examples/grafana
chmod +x setup_grafana_integration.sh
./setup_grafana_integration.sh
```

The script will:
1. Install InfluxDB 2.x
2. Install Telegraf
3. Configure Telegraf with MQTT consumer and custom processing
4. Start all services

**Time required**: ~15 minutes

### Configuration Steps

1. **Complete InfluxDB Setup**
   - Open http://localhost:8086 in your browser
   - Create initial user
   - Create organization: `sensors`
   - Create bucket: `sensor_data`
   - Generate API token and save it securely

2. **Add InfluxDB to Grafana**
   - Open Grafana: http://localhost:3000
   - Go to: Configuration → Data Sources → Add data source
   - Select: InfluxDB
   - Configure:
     - Query Language: **Flux**
     - URL: `http://localhost:8086`
     - Organization: `sensors`
     - Token: (paste your InfluxDB token)
     - Default Bucket: `sensor_data`
   - Click "Save & Test"

3. **Import Dashboard**
   - In Grafana: Dashboards → Import
   - Upload `dashboard.json` from this directory
   - Select your InfluxDB datasource
   - Click "Import"

4. **Verify Data Flow**
   ```bash
   # Check Telegraf is receiving MQTT messages
   sudo journalctl -u telegraf -f
   
   # Query InfluxDB to see data
   influx query 'from(bucket:"sensor_data") |> range(start: -1h) |> limit(n:10)'
   ```

## 📊 Dashboard Panels

The included dashboard (`dashboard.json`) provides:

1. **Temperature** - Real-time BME680 temperature (time series)
2. **Air Quality Score** - Calculated 0-100 score with color thresholds (gauge)
3. **Humidity** - BME680 relative humidity (time series)
4. **Air Quality Over Time** - Historical air quality trends (time series)
5. **Magnetic Field** - MMC5983 magnitude with baseline (time series)
6. **Light Level** - VEML7700 lux readings (time series)
7. **Magnet Detection** - Real-time status (stat panel)
8. **Person Detection** - STHS34PF80 presence status (stat panel)

## 🔧 Custom Processing

### Air Quality Calculation

Telegraf replicates the BME680 air quality algorithm from `sensor_plugins/bme680_plugin.py`:

- **Burn-in**: Collects 50 gas resistance samples to establish baseline
- **Gas Score**: Compares current resistance to baseline (75% weight)
- **Humidity Score**: Deviation from 40% ideal humidity (25% weight)
- **Output**: 0-100 score (higher = better air quality)

**Grafana Query Example:**
```flux
from(bucket: "sensor_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_field"] == "air_quality_score")
```

### Magnet Detection

Implements MMC5983 detection from `sensor_plugins/mmc5983_plugin.py`:

- **Baseline**: Rolling 20-sample average of magnetic field magnitude
- **Detection**: Triggers when magnitude > 2× baseline
- **Output**: Binary flag (0 = no magnet, 1 = magnet detected)

**Grafana Query Example:**
```flux
from(bucket: "sensor_data")
  |> range(start: -5s)
  |> filter(fn: (r) => r["_field"] == "magnet_detected")
  |> last()
```

## 🔔 Setting Up Alerts

### Example: Low Air Quality Alert

1. In Grafana, open the "Air Quality Score" panel
2. Click "Edit" → "Alert" tab → "Create alert rule"
3. Configure condition:
   - Query: `air_quality_score`
   - Condition: `IS BELOW 30`
   - For: `5 minutes`
4. Add notification channel (email, Slack, etc.)
5. Save

### Example: Magnet Detection Notification

1. Open "Magnet Detection" panel
2. Create alert rule:
   - Query: `magnet_detected`
   - Condition: `IS ABOVE 0`
   - For: `10 seconds`
3. Configure notification
4. Save

## 📁 Files in This Directory

| File | Description |
|------|-------------|
| `telegraf.conf` | Complete Telegraf configuration with MQTT consumer and custom Starlark processors |
| `dashboard.json` | Pre-built Grafana dashboard (import ready) |
| `setup_grafana_integration.sh` | Automated installation script |
| `README.md` | This file |

## 🛠️ Manual Installation

If you prefer manual setup instead of using the automated script:

### 1. Install InfluxDB

```bash
# For ARM64 (Raspberry Pi 4)
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.4-arm64.deb
sudo dpkg -i influxdb2-2.7.4-arm64.deb

# For ARMv7 (Raspberry Pi 3)
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.7.4-armhf.deb
sudo dpkg -i influxdb2-2.7.4-armhf.deb

# Start service
sudo systemctl enable influxdb
sudo systemctl start influxdb
```

Complete setup at: http://localhost:8086

### 2. Install Telegraf

```bash
# For ARM64
wget https://dl.influxdata.com/telegraf/releases/telegraf_1.29.0-1_arm64.deb
sudo dpkg -i telegraf_1.29.0-1_arm64.deb

# For ARMv7
wget https://dl.influxdata.com/telegraf/releases/telegraf_1.29.0-1_armhf.deb
sudo dpkg -i telegraf_1.29.0-1_armhf.deb
```

### 3. Configure Telegraf

```bash
# Backup existing config
sudo cp /etc/telegraf/telegraf.conf /etc/telegraf/telegraf.conf.backup

# Copy our config
sudo cp telegraf.conf /etc/telegraf/telegraf.conf

# Edit to add your InfluxDB token
sudo nano /etc/telegraf/telegraf.conf
# Replace: token = "$INFLUX_TOKEN"
# With:    token = "your-actual-token-here"

# Test configuration
sudo telegraf --test --config /etc/telegraf/telegraf.conf

# Start service
sudo systemctl enable telegraf
sudo systemctl start telegraf
```

### 4. Verify Data Flow

```bash
# Check Telegraf logs
sudo journalctl -u telegraf -f

# Test MQTT (should see JSON messages)
mosquitto_sub -h localhost -t iot_logger -v

# Query InfluxDB
influx query 'from(bucket:"sensor_data") |> range(start: -1h) |> limit(n:10)'
```

## 🐛 Troubleshooting

### No data in Grafana

**Check Telegraf logs:**
```bash
sudo journalctl -u telegraf -f
```

**Common issues:**
- MQTT broker not accessible → Check `servers = ["tcp://localhost:1883"]` in `telegraf.conf`
- No MQTT messages → Test with `mosquitto_sub -h localhost -t iot_logger`
- Wrong InfluxDB token → Verify token in `telegraf.conf`

**Test Telegraf manually:**
```bash
sudo telegraf --test --config /etc/telegraf/telegraf.conf
```

### InfluxDB connection fails

**Check InfluxDB status:**
```bash
sudo systemctl status influxdb
sudo journalctl -u influxdb -f
```

**Test InfluxDB health:**
```bash
curl http://localhost:8086/health
# Should return: {"status":"pass"}
```

### Starlark processor errors

**Enable debug mode in telegraf.conf:**
```toml
[agent]
  debug = true
```

**Restart and check logs:**
```bash
sudo systemctl restart telegraf
sudo journalctl -u telegraf -f | grep starlark
```

### Data gaps or missing fields

**Check MQTT message format:**
```bash
mosquitto_sub -h localhost -t iot_logger -v | python -m json.tool
```

Ensure JSON structure matches expected format (see `MQTT_SENSOR_PLUGIN.md`).

## 📈 Performance & Resource Usage

### Raspberry Pi Requirements

| Component | RAM | CPU | Disk |
|-----------|-----|-----|------|
| MQTT Broker | ~5 MB | <1% | ~10 MB |
| Telegraf | ~50 MB | 2-5% | ~50 MB |
| InfluxDB | ~200 MB | 5-10% | ~500 MB + data |
| Grafana | ~150 MB | 2-5% | ~100 MB |
| **Total** | **~400 MB** | **10-20%** | **~660 MB + data** |

**Minimum**: Raspberry Pi 3B+ (1GB RAM)  
**Recommended**: Raspberry Pi 4 (2GB+ RAM)

### Data Retention

InfluxDB stores data compressed. Typical storage:
- **1 sensor reading/second**: ~5 MB/day
- **30 days**: ~150 MB
- **1 year**: ~1.8 GB

**Configure retention policy:**
```flux
// Keep detailed data for 30 days
option task = {name: "retention", every: 1d}

from(bucket: "sensor_data")
  |> range(start: -30d)
  |> to(bucket: "sensor_data")

// Downsample old data (5-minute averages)
from(bucket: "sensor_data")
  |> range(start: -365d, stop: -30d)
  |> aggregateWindow(every: 5m, fn: mean)
  |> to(bucket: "sensor_data_archive")
```

## 🔗 Related Documentation

- **Strategy Document**: `../../GRAFANA_INTEGRATION_STRATEGY.md` - Complete architecture analysis
- **MQTT Plugin**: `../../MQTT_SENSOR_PLUGIN.md` - MQTT sensor data format
- **Examples**: `../MQTT_EXAMPLES_README.md` - MQTT example scripts

## 🎯 Next Steps

After successful setup:

1. **Customize Dashboard**
   - Add/remove panels
   - Adjust time ranges
   - Create different views (overview, detailed, alerts-only)

2. **Set Up Alerts**
   - Low air quality warnings
   - Temperature thresholds
   - Magnet detection notifications
   - Person presence alerts

3. **Add More Sensors**
   - Edit `telegraf.conf` to process new sensors
   - Add panels to dashboard
   - Configure alerts

4. **Optimize Performance**
   - Adjust `aggregateWindow` for slower updates
   - Configure downsampling for old data
   - Set up retention policies

## 📝 Example Flux Queries

### Temperature with Stats
```flux
from(bucket: "sensor_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_field"] == "BME68x_TemperatureC")
  |> aggregateWindow(every: 5m, fn: mean)
  |> yield(name: "mean")
```

### Air Quality Histogram
```flux
from(bucket: "sensor_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_field"] == "air_quality_score")
  |> histogram(bins: [0, 25, 50, 75, 100])
```

### Magnet Detection Events
```flux
from(bucket: "sensor_data")
  |> range(start: -24h)
  |> filter(fn: (r) => r["_field"] == "magnet_detected")
  |> filter(fn: (r) => r["_value"] == 1)
  |> aggregateWindow(every: 1m, fn: sum)
```

## 🤝 Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs: `sudo journalctl -u telegraf -f`
3. Consult documentation: `GRAFANA_INTEGRATION_STRATEGY.md`
4. Open an issue in the repository

---

**Status**: ✅ Production Ready  
**Last Updated**: 2024-02-07  
**Tested On**: Raspberry Pi 4B (4GB RAM) running Raspberry Pi OS
