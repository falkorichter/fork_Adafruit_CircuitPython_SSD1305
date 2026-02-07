#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
MQTT sensor example using Rich library for clean terminal updates.

This version uses the Rich library's Live display feature which provides
clean in-place updates without clearing the entire screen or polluting
the terminal history with escape codes.

Requires: pip install rich
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path to import sensor_plugins
sys.path.insert(0, str(Path(__file__).parent.parent))

from sensor_plugins import MQTTPlugin

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print("\n" + "=" * 60)
    print("ERROR: Rich library not installed")
    print("=" * 60)
    print("\nThis example requires the Rich library for terminal UI.")
    print("\nTo install Rich, run:")
    print("    pip install rich")
    print("\nOr install all optional dependencies:")
    print("    pip install -r optional_requirements.txt")
    print("\nFor more information, see examples/MQTT_EXAMPLES_README.md")
    print("=" * 60 + "\n")
    sys.exit(1)


def create_header_panel(mqtt_sensor):
    """Create the static header panel with connection info"""
    header_text = f"""[bold]MQTT Virtual Sensor Plugin Example[/bold]

[cyan]Broker:[/cyan] {mqtt_sensor.broker_host}:{mqtt_sensor.broker_port}
[cyan]Topic:[/cyan] {mqtt_sensor.topic}

[dim]Example JSON payload format:[/dim]
{{
    "System Info": {{"SSID": "MyWiFi", "RSSI": 198}},
    "VEML7700": {{"Lux": 50.688}},
    "MAX17048": {{"Voltage (V)": 4.21, "State Of Charge (%)": 108.89}},
    "TMP117": {{"Temperature (C)": 22.375}},
    "BME68x": {{
        "Humidity": 36.19836,
        "TemperatureC": 22.40555,
        "Pressure": 99244.27,
        "Gas Resistance": 29463.11
    }}
}}

[yellow]Press Ctrl+C to exit[/yellow]
"""
    return Panel(header_text, title="Configuration", border_style="blue")


def create_sensor_table(data):
    """Create a table with current sensor data"""
    table = Table(title="Sensor Readings", show_header=True, header_style="bold magenta")
    table.add_column("Sensor", style="cyan", width=20)
    table.add_column("Value", style="green", width=30)
    
    # Timestamp
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    table.add_row("Timestamp", timestamp)
    
    # BME68x environmental data
    table.add_row("", "")  # Spacer
    table.add_row("[bold]BME68x Environmental[/bold]", "")
    table.add_row("  Temperature", f"{data['temperature']} °C")
    table.add_row("  Humidity", f"{data['humidity']} %")
    table.add_row("  Pressure", f"{data['pressure']} Pa")
    table.add_row("  Gas Resistance", f"{data['gas_resistance']} Ω")
    
    # Air quality
    if data.get("burn_in_remaining") is not None:
        burn_in_msg = f"[yellow]Burn-in ({data['burn_in_remaining']}s remaining)[/yellow]"
        table.add_row("  Air Quality", burn_in_msg)
    else:
        # Color code air quality
        aq = data['air_quality']
        if aq == "Excellent":
            aq_display = f"[green]{aq}[/green]"
        elif aq == "Good":
            aq_display = f"[cyan]{aq}[/cyan]"
        elif aq == "Fair":
            aq_display = f"[yellow]{aq}[/yellow]"
        else:
            aq_display = f"[red]{aq}[/red]"
        table.add_row("  Air Quality", aq_display)
    
    # Other sensors
    table.add_row("", "")  # Spacer
    table.add_row("[bold]Light Sensor[/bold]", "")
    table.add_row("  VEML7700", f"{data['light']} lux")
    
    table.add_row("", "")  # Spacer
    table.add_row("[bold]Temperature Sensor[/bold]", "")
    table.add_row("  TMP117", f"{data['temp_c']} °C")
    
    table.add_row("", "")  # Spacer
    table.add_row("[bold]Battery Monitor[/bold]", "")
    table.add_row("  Voltage", f"{data['voltage']} V")
    table.add_row("  State of Charge", f"{data['soc']} %")
    
    table.add_row("", "")  # Spacer
    table.add_row("[bold]WiFi Info[/bold]", "")
    table.add_row("  SSID", f"{data['ssid']}")
    table.add_row("  RSSI", f"{data['rssi']}")
    
    return table


def create_status_panel(mqtt_sensor, data):
    """Create status panel with connection and display info"""
    if mqtt_sensor.available:
        status = "[green]✓ Connected[/green]"
    else:
        status = "[red]✗ Disconnected (waiting for broker...)[/red]"
    
    display_text = mqtt_sensor.format_display(data)
    
    status_text = f"""[bold]Connection:[/bold] {status}
[bold]Display Text:[/bold] {display_text}"""
    
    border_color = "green" if mqtt_sensor.available else "red"
    return Panel(status_text, title="Status", border_style=border_color)


def create_layout(mqtt_sensor, data):
    """Create the complete layout"""
    layout = Layout()
    
    # Split into header and body
    layout.split_column(
        Layout(create_header_panel(mqtt_sensor), size=15, name="header"),
        Layout(name="body")
    )
    
    # Split body into data and status
    layout["body"].split_column(
        Layout(create_sensor_table(data), name="data"),
        Layout(create_status_panel(mqtt_sensor, data), size=5, name="status")
    )
    
    return layout


def main():
    """Main function to demonstrate MQTT plugin with Rich UI"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="MQTT Virtual Sensor Plugin Example with Rich UI"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="MQTT broker hostname or IP address (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--topic",
        default="iot_logger",
        help="MQTT topic to subscribe to (default: iot_logger)"
    )
    args = parser.parse_args()
    
    # Create MQTT plugin instance
    mqtt_sensor = MQTTPlugin(
        broker_host=args.host,
        broker_port=args.port,
        topic=args.topic,
        check_interval=5.0,
        burn_in_time=60,  # Reduced from 300s for example
    )
    
    console = Console()
    
    try:
        with Live(console=console, refresh_per_second=1) as live:
            while True:
                # Read sensor data
                data = mqtt_sensor.read()
                
                # Create and update layout
                layout = create_layout(mqtt_sensor, data)
                live.update(layout)
                
                # Wait before next read
                time.sleep(2)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping...[/yellow]")
        console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    main()
