#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
MQTT sensor example using Textual framework for a full TUI experience.

This version uses the Textual framework to create a sophisticated terminal
UI with proper layout, reactive updates, and clean terminal handling.
Uses alternate screen buffer so it doesn't pollute terminal history.

Requires: pip install textual
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import sensor_plugins
sys.path.insert(0, str(Path(__file__).parent.parent))

from sensor_plugins import MQTTPlugin

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, VerticalScroll
    from textual.reactive import reactive
    from textual.widgets import DataTable, Footer, Header, Static
except ImportError:
    print("\n" + "=" * 60)
    print("ERROR: Textual library not installed")
    print("=" * 60)
    print("\nThis example requires the Textual framework for terminal UI.")
    print("\nTo install Textual, run:")
    print("    pip install textual")
    print("\nOr install all optional dependencies:")
    print("    pip install -r optional_requirements.txt")
    print("\nFor more information, see examples/MQTT_EXAMPLES_README.md")
    print("=" * 60 + "\n")
    sys.exit(1)


class SensorDisplay(Static):
    """Widget to display sensor information"""
    
    mqtt_sensor = None
    
    def on_mount(self) -> None:
        """Set up periodic updates when widget is mounted"""
        self.set_interval(2, self.update_sensor_data)
        self.update_sensor_data()
    
    def update_sensor_data(self) -> None:
        """Read sensor data and update display"""
        if self.mqtt_sensor is None:
            return
        
        data = self.mqtt_sensor.read()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build display text
        lines = []
        lines.append(f"[bold cyan]Timestamp:[/bold cyan] {timestamp}")
        lines.append("")
        
        # BME68x environmental data
        lines.append("[bold magenta]BME68x Environmental Sensor[/bold magenta]")
        lines.append(f"  Temperature:    {data['temperature']} °C")
        lines.append(f"  Humidity:       {data['humidity']} %")
        lines.append(f"  Pressure:       {data['pressure']} Pa")
        lines.append(f"  Gas Resistance: {data['gas_resistance']} Ω")
        
        # Air quality
        if data.get("burn_in_remaining") is not None:
            burn_in_msg = f"[yellow]Burn-in ({data['burn_in_remaining']}s remaining)[/yellow]"
            lines.append(f"  Air Quality:    {burn_in_msg}")
        else:
            aq = data['air_quality']
            if aq == "Excellent":
                lines.append(f"  Air Quality:    [green]{aq}[/green]")
            elif aq == "Good":
                lines.append(f"  Air Quality:    [cyan]{aq}[/cyan]")
            elif aq == "Fair":
                lines.append(f"  Air Quality:    [yellow]{aq}[/yellow]")
            else:
                lines.append(f"  Air Quality:    [red]{aq}[/red]")
        
        lines.append("")
        
        # Other sensors
        lines.append("[bold magenta]Light Sensor[/bold magenta]")
        lines.append(f"  VEML7700:       {data['light']} lux")
        lines.append("")
        
        lines.append("[bold magenta]Temperature Sensor[/bold magenta]")
        lines.append(f"  TMP117:         {data['temp_c']} °C")
        lines.append("")
        
        lines.append("[bold magenta]Battery Monitor[/bold magenta]")
        lines.append(f"  Voltage:        {data['voltage']} V")
        lines.append(f"  State of Charge: {data['soc']} %")
        lines.append("")
        
        lines.append("[bold magenta]WiFi Information[/bold magenta]")
        lines.append(f"  SSID:           {data['ssid']}")
        lines.append(f"  RSSI:           {data['rssi']}")
        lines.append("")
        
        # Display text and status
        display_text = self.mqtt_sensor.format_display(data)
        lines.append(f"[bold cyan]Display Text:[/bold cyan] {display_text}")
        lines.append("")
        
        if self.mqtt_sensor.available:
            lines.append("[bold green]Status: Connected ✓[/bold green]")
        else:
            lines.append("[bold red]Status: Disconnected (waiting for broker...)[/bold red]")
        
        self.update("\n".join(lines))


class ConfigDisplay(Static):
    """Widget to display configuration information"""
    
    def __init__(self, mqtt_sensor, **kwargs):
        super().__init__(**kwargs)
        self.mqtt_sensor = mqtt_sensor
    
    def on_mount(self) -> None:
        """Set up display when widget is mounted"""
        config_text = f"""[bold]MQTT Virtual Sensor Plugin[/bold]

[cyan]Broker:[/cyan] {self.mqtt_sensor.broker_host}:{self.mqtt_sensor.broker_port}
[cyan]Topic:[/cyan] {self.mqtt_sensor.topic}
[cyan]Check Interval:[/cyan] {self.mqtt_sensor.check_interval}s
[cyan]Burn-in Time:[/cyan] {self.mqtt_sensor.burn_in_time}s

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
"""
        self.update(config_text)


class MQTTSensorApp(App):
    """A Textual app to monitor MQTT sensor data"""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #config {
        height: auto;
        border: solid blue;
        padding: 1;
        margin-bottom: 1;
    }
    
    #sensors {
        height: auto;
        border: solid green;
        padding: 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]
    
    def __init__(self, mqtt_sensor, **kwargs):
        super().__init__(**kwargs)
        self.mqtt_sensor = mqtt_sensor
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app"""
        yield Header()
        yield Container(
            ConfigDisplay(self.mqtt_sensor, id="config"),
            SensorDisplay(id="sensors"),
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Configure the app when mounted"""
        self.title = "MQTT Sensor Monitor"
        self.sub_title = f"Monitoring {self.mqtt_sensor.topic}"
        
        # Pass mqtt_sensor to SensorDisplay
        sensor_display = self.query_one(SensorDisplay)
        sensor_display.mqtt_sensor = self.mqtt_sensor


def main():
    """Main function to run the Textual app"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="MQTT Virtual Sensor Plugin Example with Textual TUI"
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
    
    app = MQTTSensorApp(mqtt_sensor)
    app.run()


if __name__ == "__main__":
    main()
