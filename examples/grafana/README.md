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
1. Add InfluxDB repository
2. Install InfluxDB 2.x server and CLI tools
3. Automatically configure InfluxDB (organization, bucket, credentials)
4. Install Telegraf
5. Configure Telegraf with MQTT consumer and custom processing
6. Start all services

**Important**: If you have InfluxDB 1.x installed, the script will detect it and ask you to uninstall it first, as this integration requires InfluxDB 2.x.

**Time required**: ~10-15 minutes (fully automated, no manual steps)

### Automated Installation

The setup script now performs **fully automated installation** including:
- InfluxDB installation via APT repository
- Automated InfluxDB configuration using CLI (no web UI required)
- Automatic token generation and configuration
- Telegraf installation and configuration

```bash
cd examples/grafana
chmod +x setup_grafana_integration.sh
./setup_grafana_integration.sh
```

The script will:
1. Add InfluxDB repository and install InfluxDB 2.x
2. Automatically configure InfluxDB with:
   - Organization: `sensors`
   - Bucket: `sensor_data`
   - Auto-generated credentials (saved to `~/influxdb_credentials.txt`)
3. Install Telegraf from the repository
4. Configure Telegraf with the generated InfluxDB token
5. Start all services and verify connectivity

**No manual setup required!** The script handles everything automatically.

### Adding InfluxDB to Grafana

After the automated setup completes:

1. **Add InfluxDB Datasource to Grafana**
   - Open Grafana: http://localhost:3000
   - Go to: Configuration → Data Sources → Add data source
   - Select: InfluxDB
   - Configure:
     - Query Language: **Flux**
     - URL: `http://localhost:8086`
     - Organization: `sensors`
     - Token: (use the token from the setup script output or `~/influxdb_credentials.txt`)
     - Default Bucket: `sensor_data`
   - Click "Save & Test"

2. **Import Dashboard**
   
   Two dashboard options are available:
   
   **Option A: Simplified Dashboard (Recommended for first-time setup)**
   - File: `dashboard_simple.json`
   - Uses datasource selector (choose during import)
   - Simple Flux queries that work with any field names
   - Easy to customize per your data structure
   - Best for troubleshooting and learning
   
   **Option B: Full-Featured Dashboard**
   - File: `dashboard.json`
   - Requires exact field names from telegraf.conf
   - More polished visualizations
   - Use after verifying data is flowing correctly
   
   **Import Steps:**
   - In Grafana: Dashboards → Import
   - Upload your chosen dashboard file
   - Select your InfluxDB datasource when prompted
   - Click "Import"

3. **Verify Data Flow**
   ```bash
   # Check Telegraf is receiving MQTT messages
   sudo journalctl -u telegraf -f
   
   # Query InfluxDB to see data
   influx query 'from(bucket:"sensor_data") |> range(start: -1h) |> limit(n:10)'
   ```

## 📊 Dashboard Panels

Both dashboards provide 8 sensor visualization panels:

1. **Temperature (°C)** - Real-time BME680 temperature (time series)
2. **Humidity (%)** - BME680 relative humidity (time series)
3. **Air Quality Score** - Calculated 0-100 score with color thresholds (gauge)
4. **Air Quality Over Time** - Historical air quality trends (time series)
5. **Light Level (Lux)** - VEML7700 light readings (time series)
6. **Magnetic Field (µT)** - MMC5983 magnitude with baseline (time series)
7. **Magnet Detection** - Real-time status (stat panel)
8. **Person Detection** - STHS34PF80 presence status (stat panel)

### Dashboard Differences

**dashboard_simple.json** (Recommended for initial setup):
- Uses `datasource: null` (select datasource during import)
- Simpler Flux queries for easier customization
- No measurement filters (works with any MQTT data structure)
- Queries calculated fields: `air_quality_score`, `magnet_detected`, `person_detected`, etc.

**dashboard.json** (Full-featured):
- Uses templated datasource variable `${DS_INFLUXDB}`
- Includes measurement filters and aggregation windows
- More sophisticated query patterns
- Requires exact field names from telegraf.conf

## 🔧 Custom Processing

### Field Reference

Telegraf processes MQTT sensor data and creates the following fields:

**Raw Sensor Fields** (passed through from MQTT):
- `BME68x_TemperatureC` - Temperature in Celsius
- `BME68x_Humidity` - Relative humidity percentage
- `BME68x_Gas Resistance` - Gas sensor resistance (Ohms)
- `VEML7700_Lux` - Light level in lux
- `MMC5983_X Field (Gauss)`, `MMC5983_Y Field (Gauss)`, `MMC5983_Z Field (Gauss)` - Magnetic field components
- `STHS34PF80_PresenceValue`, `STHS34PF80_MotionValue` - IR presence sensor readings

**Calculated Fields** (created by Starlark processors):
- `air_quality_score` - BME680 air quality (0-100, higher is better)
- `gas_baseline` - Rolling average of gas resistance (for air quality calculation)
- `mag_magnitude` - 3D magnetic field magnitude in Gauss
- `mag_baseline` - Median of clean (non-detection) samples (MAD baseline)
- `mag_z_score` - Robust z-score for current reading (MAD-based)
- `magnet_detected` - Binary flag (0 or 1) indicating nearby magnet
- `person_detected` - Binary flag (0 or 1) indicating person presence

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

Implements robust MMC5983 detection from `sensor_plugins/magnet_detector.py` using Median Absolute Deviation (MAD):

- **Baseline**: Median of up to 50 clean (non-detection) samples — not polluted by magnet readings
- **MAD-based anomaly detection**: Robust z-score = |magnitude − median| / (MAD × 1.4826)
- **Hysteresis (Schmitt trigger)**: Triggers at z-score > 5.0σ, releases at < 3.0σ — prevents oscillation
- **Bidirectional**: Detects both magnet approach (field increase) and removal (field decrease)
- **Output**: Binary flag (0 = no magnet, 1 = magnet detected), plus `mag_z_score` for diagnostics

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
# Add InfluxDB repository (using preferred key with fingerprint verification)
wget -q https://repos.influxdata.com/influxdata-archive.key
gpg --show-keys --with-fingerprint --with-colons ./influxdata-archive.key 2>&1 | grep -q '^fpr:\+24C975CBA61A024EE1B631787C3D57159FC2F927:$' && cat influxdata-archive.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive.gpg > /dev/null

echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list

# Install InfluxDB
sudo apt-get update
sudo apt-get install -y influxdb2 influxdb2-cli

# Start service
sudo systemctl enable influxdb
sudo systemctl start influxdb
```

### 2. Configure InfluxDB (automated via CLI)

```bash
# Generate a secure password
INFLUX_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Automated setup using influx CLI
influx setup \
  --username admin \
  --password "$INFLUX_PASSWORD" \
  --org sensors \
  --bucket sensor_data \
  --retention 0 \
  --force

# Get the token
INFLUX_TOKEN=$(influx auth list --json | grep -o '"token":"[^"]*"' | head -1 | cut -d'"' -f4)

echo "Token: $INFLUX_TOKEN"
echo "Password: $INFLUX_PASSWORD"
```

**Note**: The `influx` CLI command is provided by the `influxdb2-cli` package.

### 3. Install Telegraf

```bash
# Repository already added from InfluxDB installation
sudo apt-get install -y telegraf
```

### 4. Configure Telegraf

```bash
# Backup existing config
sudo cp /etc/telegraf/telegraf.conf /etc/telegraf/telegraf.conf.backup

# Copy our config
sudo cp telegraf.conf /etc/telegraf/telegraf.conf

# Replace token placeholder with actual token
sudo sed -i "s/\$INFLUX_TOKEN/$INFLUX_TOKEN/g" /etc/telegraf/telegraf.conf

# Test configuration
sudo telegraf --test --config /etc/telegraf/telegraf.conf

# Start service
sudo systemctl enable telegraf
sudo systemctl start telegraf
```

### 5. Verify Data Flow

```bash
# Check Telegraf logs
sudo journalctl -u telegraf -f

# Test MQTT (should see JSON messages)
mosquitto_sub -h localhost -t iot_logger -v

# Query InfluxDB
influx query 'from(bucket:"sensor_data") |> range(start: -1h) |> limit(n:10)'
```

## 🐛 Troubleshooting

### GPG Key Errors (NO_PUBKEY)

If you encounter GPG key verification errors, this is due to InfluxData's GPG key rotation system. The setup script handles this automatically with fingerprint verification, but if you see this error:

```bash
W: GPG error: https://repos.influxdata.com/debian stable InRelease: The following signatures couldn't be verified because the public key is not available: NO_PUBKEY DA61C26A0585BD3B
```

**Manual fix (using preferred method):**

```bash
# Download and verify the preferred key (with subkeys)
wget -q https://repos.influxdata.com/influxdata-archive.key
gpg --show-keys --with-fingerprint --with-colons ./influxdata-archive.key 2>&1 | grep -q '^fpr:\+24C975CBA61A024EE1B631787C3D57159FC2F927:$' && cat influxdata-archive.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive.gpg > /dev/null

# Update repository list
echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list

# Then update
sudo apt-get update
```

**Alternative (keyserver fallback):**

```bash
# Fetch from keyserver if URL is blocked
sudo gpg --keyserver keyserver.ubuntu.com --recv-keys DA61C26A0585BD3B
sudo gpg --export DA61C26A0585BD3B | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive.gpg > /dev/null
sudo apt-get update
```

**Note**: InfluxData uses a primary GPG key with rotating subkeys. The preferred `influxdata-archive.key` contains the primary key and all active subkeys. The current subkey (DA61C26A0585BD3B) expires 2029-01-17. See: https://repos.influxdata.com/debian

### "influx command not found"

If you see this error, install the InfluxDB CLI tools:

```bash
sudo apt-get install influxdb2-cli
```

### InfluxDB 1.x detected

If the script detects InfluxDB 1.x (config at `/etc/influxdb/influxdb.conf`), you need to uninstall it first:

```bash
# Stop and remove InfluxDB 1.x
sudo systemctl stop influxdb
sudo apt-get remove influxdb
sudo rm -rf /etc/influxdb /var/lib/influxdb

# Then run the setup script again
cd examples/grafana
./setup_grafana_integration.sh
```

**Note**: InfluxDB 1.x and 2.x are not compatible. This integration requires InfluxDB 2.x for the CLI-based automated setup and Flux query language support.

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

### Dashboard shows "No Data" or empty panels

If the dashboard displays but panels show "No Data":

**1. Verify data is in InfluxDB:**
```bash
influx query 'from(bucket:"sensor_data") |> range(start: -1h) |> limit(n:10)'
```

If this returns data, the problem is with the dashboard queries.

**2. Use the simplified dashboard:**

The `dashboard_simple.json` is designed for easier troubleshooting:
- Import `dashboard_simple.json` instead of `dashboard.json`
- Select your InfluxDB datasource during import
- Queries don't require specific measurement names
- Field names match telegraf.conf output

**3. Check field names in your data:**

```bash
# List all fields in your data
influx query 'from(bucket:"sensor_data") |> range(start: -1h) |> keys() |> keep(columns: ["_field"]) |> distinct()'
```

**4. Update dashboard queries:**

If field names don't match, edit each panel:
- Click panel title → Edit
- Modify the `filter` line to match your actual field names
- Example: Change `r["_field"] == "BME68x_TemperatureC"` to match your field name

**5. Common field name mismatches:**

The queries expect these field names (set in telegraf.conf):
- `BME68x_TemperatureC` - Temperature in Celsius
- `BME68x_Humidity` - Humidity percentage  
- `air_quality_score` - Air quality score (0-100)
- `VEML7700_Lux` - Light level in lux
- `mag_magnitude` - Magnetic field magnitude
- `mag_baseline` - Magnetic field baseline (MAD-based median)
- `mag_z_score` - Robust z-score for magnet detection
- `magnet_detected` - Magnet detection flag (0/1)
- `person_detected` - Person detection flag (0/1)

**Note**: The field is named `air_quality_score` (not `air_quality`). If queries show no data, verify field names with the command in step 3 above.

### After pulling code updates

**If you get Starlark syntax errors after pulling repository updates**, you need to update your installed telegraf.conf:

```bash
# Copy the updated config to the system location
sudo cp examples/grafana/telegraf.conf /etc/telegraf/telegraf.conf

# Replace the token placeholder with your actual token
INFLUX_TOKEN=$(cat ~/influxdb_credentials.txt | grep "Token:" | cut -d' ' -f2)
sudo sed -i "s/\$INFLUX_TOKEN/$INFLUX_TOKEN/g" /etc/telegraf/telegraf.conf

# Test the configuration
sudo telegraf --test --config /etc/telegraf/telegraf.conf

# If test passes, restart Telegraf
sudo systemctl restart telegraf
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
