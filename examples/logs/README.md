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
python3 serve.py
# Open http://localhost:8000/visualizer.html
```

The included `serve.py` also provides a **CORS proxy** so the visualizer can download files directly from the DataLogger device (which doesn't send `Access-Control-Allow-Origin` headers). If you use `python3 -m http.server` instead, downloads from the DataLogger will be blocked by the browser's CORS policy.

You can also drag-and-drop or upload any CSV/TXT file from the SparkFun DataLogger.

### Screenshots

**Landing page** — select a log file, upload your own, or connect to a DataLogger on the network:

![Landing page with file selector, DataLogger download panel, and settings](https://github.com/user-attachments/assets/5b4c492d-4d52-4281-bc79-a7a6c6fc5199)

**Dashboard with sfe0009.txt** — stats cards show file metadata, followed by charts grouped by sensor category (temperature, light, humidity, air quality, battery, magnetic field, presence, system info). Calculated fields (air quality score, magnet detection, person present) are computed automatically:

![Dashboard showing sfe0009.txt with stats cards and sensor charts](https://github.com/user-attachments/assets/147c7b63-3633-48e5-a85a-0c833892647e)

**Full dashboard view** — all 12 chart groups rendered for sfe0009.txt, including calculated derived fields:

![Full page view of all chart groups for sfe0009.txt](https://github.com/user-attachments/assets/71a3fc3d-4ab5-4a94-b593-720fbf19f852)

**Settings panel** — adjust thresholds for person detection, air quality scoring, and magnet detection, then click "Apply & Recalculate":

![Settings panel with adjustable thresholds for all calculated fields](https://github.com/user-attachments/assets/1a01f563-0ce9-486d-b299-b1845ae986f4)

### Features

- **Zoom & pan**: scroll wheel to zoom, drag to pan, double-click to reset
- **Combined view**: click "📊 All Files" to merge all log files into one dashboard with per-file colored series
- **Calculated fields**: person present (STHS34PF80), air quality score (BME680), magnet detection (MMC5983) — same algorithms as the Python plugins and Telegraf Starlark processor
- **Smart X-axis**: uses `General.Time` timestamps when available, falls back to `System Info.Uptime` or sample index

### Download from DataLogger

The visualizer can connect directly to a SparkFun DataLogger on your network to browse and download log files. Expand the "📡 Download from DataLogger" panel, enter the logger URL (e.g., `http://datalogger5b7a0.local`), and click **Connect**. Select which files to download and click **Download & Visualize Selected**.

> **Note:** The DataLogger does not send CORS headers, so file downloads require the CORS proxy provided by `serve.py`. The visualizer auto-detects whether the proxy is available and shows a warning if it isn't.

## Grafana Import

See **[GRAFANA_CSV_IMPORT.md](GRAFANA_CSV_IMPORT.md)** for instructions on importing these CSV logs into InfluxDB/Grafana, including deduplication strategies to avoid duplicate data when WiFi was intermittent.
