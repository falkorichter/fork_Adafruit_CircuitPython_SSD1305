# Sensor Log Files

This folder contains CSV log files written directly by the [SparkFun DataLogger](https://docs.sparkfun.com/SparkFun_DataLogger/introduction/) as a backup when WiFi/MQTT may be unavailable.

## Files

| File | Sensors | Rows |
|------|---------|------|
| `sfe0001.txt` | VEML7700, MAX17048, TMP117, BME68x | ~4,350 |
| `sfe0002.txt` | VEML7700, MAX17048, TMP117, BME68x | ~1,220 |
| `sfe0003.txt` | VEML7700, MAX17048, TMP117, BME68x | ~4,240 |
| `sfe0005.txt` | System Info, VEML7700, MMC5983, MAX17048, TMP117, STHS34PF80, BME68x | ~4,270 |
| `sfe0006.txt` | VEML7700, MMC5983, MAX17048, TMP117, STHS34PF80 | ~900 |
| `sfe0009.txt` | General (Entry/Time), System Info, VEML6075, MMC5983, MAX17048, TMP117, STHS34PF80, BME68x | ~40 |

## Visualizer

Open **[visualizer.html](visualizer.html)** in a browser to view interactive charts of the log data.

To load the built-in log files, serve this folder with a local HTTP server:

```bash
cd examples/logs
python3 -m http.server 8000
# Open http://localhost:8000/visualizer.html
```

You can also drag-and-drop or upload any CSV/TXT file from the SparkFun DataLogger.

## Grafana Import

See **[GRAFANA_CSV_IMPORT.md](GRAFANA_CSV_IMPORT.md)** for instructions on importing these CSV logs into InfluxDB/Grafana, including deduplication strategies to avoid duplicate data when WiFi was intermittent.
