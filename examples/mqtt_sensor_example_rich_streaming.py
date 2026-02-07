#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
MQTT sensor example using Rich library - WebSocket Streaming Compatible Version.

This version is optimized for WebSocket streaming by:
1. Configuring Rich Console to use sys.stdout explicitly
2. Using periodic console.print() instead of Live() display
3. Avoiding terminal features that bypass stdout capture

For local terminal use, prefer mqtt_sensor_example_rich.py which uses Live display.
For WebSocket streaming, use this version.

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


# Configure Rich Console for WebSocket streaming compatibility
# - file=sys.stdout: Use stdout (which may be TerminalStreamer)
# - force_terminal=True: Treat stdout as terminal even if redirected
# - force_interactive=False: Disable interactive features that bypass stdout
# - width=100: Fixed width for consistent rendering
console = Console(
    file=sys.stdout,
    force_terminal=True,
    force_interactive=False,
    width=100,
    height=30,
    legacy_windows=False
)


def create_header_panel(mqtt_sensor):
    """Create the static header panel with connection info"""
    header_text = f"""[bold]MQTT Virtual Sensor Plugin Example[/bold]
[dim]WebSocket Streaming Compatible Version[/dim]

[yellow]Broker:[/yellow] {mqtt_sensor.broker_host}:{mqtt_sensor.broker_port}
[yellow]Topic:[/yellow] {mqtt_sensor.topic}
"""
    
    if mqtt_sensor.available:
        status = "[green]● Connected[/green]"
    else:
        status = "[red]○ Disconnected[/red]"
    
    header_text += f"\n[yellow]Status:[/yellow] {status}"
    
    return Panel(
        header_text,
        title="[bold cyan]MQTT Sensor Monitor[/bold cyan]",
        border_style="cyan"
    )


def create_sensor_table_left(data, mqtt_sensor):
    """Create left column table with sensor readings"""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Sensor", style="cyan", width=18)
    table.add_column("Value", style="green", width=25)
    
    # Environmental sensors (BME680)
    table.add_row("[bold magenta]Environmental (BME680)[/bold magenta]", "")
    table.add_row("  Temperature", f"{data['temperature']} °C")
    table.add_row("  Humidity", f"{data['humidity']} %")
    table.add_row("  Pressure", f"{data['pressure']} Pa")
    table.add_row("  Gas Resistance", f"{data['gas_resistance']} Ω")
    
    # Air quality - handle burn-in period and numeric values
    if data.get("burn_in_remaining") is not None:
        burn_in_msg = f"[yellow]Burn-in ({data['burn_in_remaining']}s remaining)[/yellow]"
        table.add_row("  Air Quality", burn_in_msg)
    elif data['air_quality'] == "n/a":
        table.add_row("  Air Quality", str(data['air_quality']))
    else:
        # Format numeric air quality value
        table.add_row("  Air Quality", f"{data['air_quality']:.1f}")
    
    table.add_row("", "")
    
    # Light sensor (VEML7700)
    table.add_row("[bold magenta]Light (VEML7700)[/bold magenta]", "")
    table.add_row("  Ambient Light", f"{data['light']} lux")
    
    table.add_row("", "")
    
    # Temperature sensor (TMP117)
    table.add_row("[bold magenta]Precision Temp (TMP117)[/bold magenta]", "")
    table.add_row("  Temperature", f"{data['temp_c']} °C")
    
    table.add_row("", "")
    
    # Human presence sensor (STHS34PF80)
    table.add_row("[bold magenta]Presence (STHS34PF80)[/bold magenta]", "")
    table.add_row("  Presence", f"{data['presence_value']} cm⁻¹")
    table.add_row("  Motion", f"{data['motion_value']} LSB")
    table.add_row("  Object Temp", f"{data['sths34_temperature']} °C")
    
    # Person detection status with color coding
    person_status = data.get('person_detected')
    if person_status is None or person_status == 'n/a':
        table.add_row("  Person Status", "[dim]UNKNOWN - No data[/dim]")
    elif person_status:
        table.add_row("  Person Status", "[red bold]*** DETECTED ***[/red bold]")
    else:
        table.add_row("  Person Status", "[green]Not detected[/green]")
    
    return table


def create_sensor_table_right(data, mqtt_sensor):
    """Create right column table with system information"""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Sensor", style="cyan", width=18)
    table.add_column("Value", style="green", width=25)
    
    # Battery monitor
    table.add_row("[bold magenta]Battery Monitor[/bold magenta]", "")
    table.add_row("  Voltage", f"{data['voltage']} V")
    table.add_row("  State of Charge", f"{data['soc']} %")
    
    table.add_row("", "")
    
    # WiFi information
    table.add_row("[bold magenta]WiFi Information[/bold magenta]", "")
    table.add_row("  SSID", f"{data['ssid']}")
    table.add_row("  RSSI", f"{data['rssi']}")
    
    table.add_row("", "")
    
    # Display text and status
    display_text = mqtt_sensor.format_display(data)
    table.add_row("[bold magenta]Display Output[/bold magenta]", "")
    table.add_row("  ", display_text)
    
    table.add_row("", "")
    
    # Connection status
    if mqtt_sensor.available:
        table.add_row("[bold]Status[/bold]", "[green]✓ Connected[/green]")
    else:
        table.add_row("[bold]Status[/bold]", "[red]✗ Disconnected[/red]")
    
    return table


def create_layout(data, mqtt_sensor):
    """Create the complete display layout"""
    layout = Layout()
    
    # Create header
    header = create_header_panel(mqtt_sensor)
    
    # Create two-column layout for sensor data
    left_table = create_sensor_table_left(data, mqtt_sensor)
    right_table = create_sensor_table_right(data, mqtt_sensor)
    
    # Combine tables side by side
    combined_table = Table.grid(padding=2)
    combined_table.add_column()
    combined_table.add_column()
    combined_table.add_row(left_table, right_table)
    
    # Create footer
    footer = Panel(
        "[dim]Press Ctrl+C to exit | Updates every 2 seconds[/dim]",
        border_style="dim"
    )
    
    # Assemble layout
    layout.split_column(
        Layout(header, size=8),
        Layout(combined_table),
        Layout(footer, size=3)
    )
    
    return layout


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MQTT sensor monitor with Rich UI (WebSocket streaming compatible)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="MQTT broker hostname (default: localhost)"
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
    
    # Create MQTT sensor plugin
    mqtt_sensor = MQTTPlugin(
        broker_host=args.host,
        broker_port=args.port,
        topic=args.topic,
        check_interval=5.0,
        burn_in_time=60,
    )
    
    # Print initial message
    console.print(f"\n[bold cyan]MQTT Virtual Sensor Plugin Example (Rich - Streaming)[/bold cyan]")
    console.print(f"[dim]Optimized for WebSocket streaming[/dim]\n")
    console.print(f"Connecting to MQTT broker at {args.host}:{args.port}")
    console.print(f"Subscribing to topic: {args.topic}\n")
    console.print("[yellow]Reading sensor data (Ctrl+C to exit)...[/yellow]\n")
    
    try:
        while True:
            # Get sensor data
            data = mqtt_sensor.read()
            
            # Clear screen for next update
            # This sends ANSI clear codes which will be captured by TerminalStreamer
            console.clear()
            
            # Create and print layout
            layout = create_layout(data, mqtt_sensor)
            console.print(layout)
            
            # Wait before next update
            time.sleep(2)
            
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Stopping...[/yellow]")
    finally:
        console.print("[green]Goodbye![/green]")


if __name__ == "__main__":
    main()
