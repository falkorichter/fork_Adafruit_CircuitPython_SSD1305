# Grafana CSV Log Import Guide

This guide explains how to import SparkFun DataLogger CSV log files into InfluxDB/Grafana, especially useful when WiFi was offline and MQTT data wasn't delivered in real-time.

## Overview

When the IoT sensor logger loses WiFi connectivity, MQTT messages aren't delivered to the TIG stack (Telegraf → InfluxDB → Grafana). The SparkFun DataLogger writes CSV backup files to its SD card. This guide covers importing those CSV files into InfluxDB while avoiding duplicate data points.

## Deduplication Strategy

### The Problem
If WiFi was intermittent, some data points may have been delivered via MQTT *and* written to CSV. Importing the entire CSV would create duplicates in InfluxDB.

### Unique Identifier Approach

The SparkFun DataLogger (firmware ≥ recent versions) supports adding metadata columns:

- **`General.Entry`** — Sequential row counter per log file
- **`General.Time`** — ISO 8601 timestamp (e.g., `2026-02-08T05:29:32`)

These two fields together form a natural unique identifier. To enable them, configure the DataLogger to include the "General" output in its CSV logging settings (see [SparkFun DataLogger docs](https://docs.sparkfun.com/SparkFun_DataLogger/introduction/)).

> **Tip:** In the SparkFun DataLogger settings, enable **"General"** as a data source to ensure `General.Entry` and `General.Time` columns are included in every log file. The `sfe0009.txt` file in this repo demonstrates this format.

### How InfluxDB Handles Duplicates

InfluxDB uses a combination of **measurement name**, **tag set**, and **timestamp** as the unique key for each point. If you write a point with the same measurement, tags, and timestamp as an existing point, **InfluxDB overwrites it** rather than creating a duplicate.

This means:
- If we use `General.Time` as the InfluxDB timestamp, re-importing the same CSV data is **idempotent** — it simply overwrites identical points.
- Adding a `source` tag (e.g., `source=csv_import` vs `source=mqtt`) lets you distinguish imported data from live data while still deduplicating on timestamp.

## Import Methods

### Method 1: Python Import Script (Recommended)

Use the InfluxDB Python client to import CSV files directly.

#### Prerequisites

```bash
pip install influxdb-client
```

#### Import Script

```python
#!/usr/bin/env python3
"""Import SparkFun DataLogger CSV files into InfluxDB 2.x."""

import csv
import sys
import argparse
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

def parse_csv_row(headers, values):
    """Parse a CSV row into a dict, converting numeric values."""
    row = {}
    for h, v in zip(headers, values):
        v = v.strip()
        try:
            row[h] = float(v)
        except ValueError:
            row[h] = v
    return row

def csv_to_points(filepath, measurement="iot_sensor"):
    """Convert a CSV file to InfluxDB points."""
    points = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        headers = [h.strip() for h in next(reader)]
        
        has_time = 'General.Time' in headers
        has_entry = 'General.Entry' in headers
        has_uptime = 'System Info.Uptime' in headers
        
        # Tags (string metadata)
        tag_columns = {'System Info.SSID'}
        # Skip columns (not sensor data)
        skip_columns = {'General.Entry', 'General.Time', 'System Info.SSID'}
        
        for row_idx, values in enumerate(reader):
            if len(values) != len(headers):
                continue
            
            row = parse_csv_row(headers, values)
            p = Point(measurement)
            
            # Set timestamp
            if has_time:
                try:
                    ts = datetime.fromisoformat(row['General.Time'])
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    p.time(ts, WritePrecision.S)
                except (ValueError, KeyError):
                    continue  # Skip rows with invalid timestamps
            
            # Add tags for deduplication and filtering
            p.tag("source", "csv_import")
            p.tag("file", filepath.split('/')[-1])
            if has_entry:
                try:
                    p.tag("entry", str(int(row['General.Entry'])))
                except (ValueError, KeyError):
                    pass
            if 'System Info.SSID' in row:
                p.tag("ssid", str(row['System Info.SSID']))
            
            # Add all numeric fields
            for h in headers:
                if h in skip_columns:
                    continue
                if h in row and isinstance(row[h], float):
                    # Use simplified field names matching MQTT format
                    field_name = h.replace(' ', '_')
                    p.field(field_name, row[h])
            
            points.append(p)
    
    return points

def main():
    parser = argparse.ArgumentParser(description='Import CSV logs into InfluxDB')
    parser.add_argument('files', nargs='+', help='CSV/TXT log files to import')
    parser.add_argument('--url', default='http://localhost:8086', help='InfluxDB URL')
    parser.add_argument('--token', required=True, help='InfluxDB API token')
    parser.add_argument('--org', default='iot_org', help='InfluxDB organization')
    parser.add_argument('--bucket', default='iot_bucket', help='InfluxDB bucket')
    parser.add_argument('--measurement', default='iot_sensor', help='Measurement name')
    parser.add_argument('--dry-run', action='store_true', help='Parse files without writing')
    parser.add_argument('--batch-size', type=int, default=500, help='Write batch size')
    args = parser.parse_args()
    
    all_points = []
    for filepath in args.files:
        print(f"Parsing {filepath}...")
        points = csv_to_points(filepath, args.measurement)
        print(f"  → {len(points)} data points")
        all_points.extend(points)
    
    print(f"\nTotal: {len(all_points)} points from {len(args.files)} file(s)")
    
    if args.dry_run:
        print("Dry run — no data written.")
        return
    
    print(f"Writing to {args.url} ({args.org}/{args.bucket})...")
    with InfluxDBClient(url=args.url, token=args.token, org=args.org) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        for i in range(0, len(all_points), args.batch_size):
            batch = all_points[i:i + args.batch_size]
            write_api.write(bucket=args.bucket, record=batch)
            print(f"  Written {min(i + args.batch_size, len(all_points))}/{len(all_points)}")
    
    print("Import complete!")

if __name__ == '__main__':
    main()
```

#### Usage

```bash
# Import a single file
python3 import_csv_to_influxdb.py sfe0009.txt \
    --token "your-influxdb-token" \
    --org iot_org --bucket iot_bucket

# Import all log files
python3 import_csv_to_influxdb.py examples/logs/sfe*.txt \
    --token "your-influxdb-token" \
    --org iot_org --bucket iot_bucket

# Dry run (parse only, no write)
python3 import_csv_to_influxdb.py examples/logs/sfe0009.txt --dry-run
```

### Method 2: Telegraf File Input (Batch Import)

Use Telegraf's `file` input plugin to read CSV files. Add this to your `telegraf.conf`:

```toml
# Temporary input for CSV import — remove after import is complete
[[inputs.file]]
  files = ["/path/to/examples/logs/sfe0009.txt"]
  data_format = "csv"
  csv_header_row_count = 1
  csv_timestamp_column = "General.Time"
  csv_timestamp_format = "2006-01-02T15:04:05"
  csv_tag_columns = ["System Info.SSID"]
  csv_skip_columns = ["General.Entry"]
  
  [inputs.file.tags]
    source = "csv_import"
```

Then run Telegraf once:
```bash
telegraf --config telegraf_import.conf --once
```

> **Note:** This method works best for files that include `General.Time` timestamps. For files without timestamps, use the Python script (Method 1) instead.

### Method 3: InfluxDB CLI (Line Protocol)

Convert CSV to InfluxDB line protocol format and use the `influx write` command:

```bash
# Convert CSV to line protocol (using the Python script with --dry-run output)
python3 import_csv_to_influxdb.py sfe0009.txt --dry-run > /tmp/import_preview.txt

# Write directly via CLI
influx write --bucket iot_bucket --org iot_org \
    --token "your-token" \
    --file /path/to/lineprotocol.txt
```

## Handling Files Without Timestamps

Older log files (`sfe0001.txt` through `sfe0006.txt`) don't include `General.Time`. For these:

1. **Use file metadata**: Derive approximate timestamps from the file's creation date and the `System Info.Uptime` column (milliseconds since device boot).
2. **Synthetic timestamps**: Calculate `file_start_time + uptime_ms` for each row.
3. **Separate bucket**: Import into a separate InfluxDB bucket (e.g., `iot_historical`) to keep them distinct from live data.

**Recommendation:** Configure the SparkFun DataLogger to always include `General.Entry` and `General.Time` columns going forward. This ensures all future CSV logs can be cleanly imported and deduplicated.

## Avoiding Duplicates — Summary

| Scenario | Strategy |
|----------|----------|
| CSV has `General.Time` | Use as InfluxDB timestamp — duplicate writes are idempotent |
| WiFi was fully offline | Import entire CSV safely — no MQTT data exists for that period |
| WiFi was intermittent | Import CSV — InfluxDB overwrites matching timestamps automatically |
| Re-importing same file | Safe — identical points overwrite, no duplicates created |
| Multiple log files overlap | Tag with `file` name — timestamps + tags ensure uniqueness |

## SparkFun DataLogger Configuration

To ensure CSV logs support clean imports, configure the DataLogger ([docs](https://docs.sparkfun.com/SparkFun_DataLogger/introduction/)):

1. **Enable General output**: Adds `General.Entry` (row counter) and `General.Time` (ISO timestamp)
2. **Enable System Info**: Adds `System Info.SSID`, `System Info.Uptime` for context
3. **Set consistent interval**: Match the MQTT publish interval (default 15s) so CSV and MQTT data align
4. **Use NTP sync**: Ensure the device clock is accurate for timestamp-based deduplication

See the [SparkFun DataLogger repository](https://github.com/falkorichter/SparkFun_DataLogger) and [documentation](https://github.com/sparkfun/SparkFun_DataLogger/tree/main/docs) for full configuration details.
