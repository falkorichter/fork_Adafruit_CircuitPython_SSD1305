#!/usr/bin/env python3
"""
Quick demo of the Rich-based terminal UI without MQTT broker.
This simulates sensor data to show how the UI looks.
"""

import random
import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table


def create_demo_data(counter):
    """Generate simulated sensor data"""
    return {
        'temperature': f"{22.0 + random.uniform(-0.5, 0.5):.2f}",
        'humidity': f"{45.0 + random.uniform(-2, 2):.2f}",
        'pressure': f"{99200 + random.uniform(-50, 50):.2f}",
        'gas_resistance': f"{28000 + random.uniform(-1000, 1000):.0f}",
        'air_quality': random.choice(['Excellent', 'Good', 'Fair']),
        'light': f"{50.0 + random.uniform(-5, 5):.2f}",
        'temp_c': f"{22.5 + random.uniform(-0.3, 0.3):.2f}",
        'voltage': f"{4.2 + random.uniform(-0.05, 0.05):.2f}",
        'soc': f"{95 + random.uniform(-2, 2):.1f}",
        'ssid': 'HomeWiFi',
        'rssi': f"{-45 + random.randint(-5, 5)}",
    }


def create_sensor_table(data, counter):
    """Create a table with current sensor data"""
    table = Table(title="Sensor Readings", show_header=True, header_style="bold magenta")
    table.add_column("Sensor", style="cyan", width=20)
    table.add_column("Value", style="green", width=30)
    
    # Timestamp
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    table.add_row("Timestamp", timestamp)
    table.add_row("Update Count", str(counter))
    
    # BME68x environmental data
    table.add_row("", "")
    table.add_row("[bold]BME68x Environmental[/bold]", "")
    table.add_row("  Temperature", f"{data['temperature']} °C")
    table.add_row("  Humidity", f"{data['humidity']} %")
    table.add_row("  Pressure", f"{data['pressure']} Pa")
    table.add_row("  Gas Resistance", f"{data['gas_resistance']} Ω")
    
    # Air quality
    aq = data['air_quality']
    if aq == "Excellent":
        aq_display = f"[green]{aq}[/green]"
    elif aq == "Good":
        aq_display = f"[cyan]{aq}[/cyan]"
    else:
        aq_display = f"[yellow]{aq}[/yellow]"
    table.add_row("  Air Quality", aq_display)
    
    # Other sensors
    table.add_row("", "")
    table.add_row("[bold]Light Sensor[/bold]", "")
    table.add_row("  VEML7700", f"{data['light']} lux")
    
    table.add_row("", "")
    table.add_row("[bold]Temperature Sensor[/bold]", "")
    table.add_row("  TMP117", f"{data['temp_c']} °C")
    
    table.add_row("", "")
    table.add_row("[bold]Battery Monitor[/bold]", "")
    table.add_row("  Voltage", f"{data['voltage']} V")
    table.add_row("  State of Charge", f"{data['soc']} %")
    
    table.add_row("", "")
    table.add_row("[bold]WiFi Info[/bold]", "")
    table.add_row("  SSID", f"{data['ssid']}")
    table.add_row("  RSSI", f"{data['rssi']}")
    
    return table


def main():
    """Run the demo"""
    console = Console()
    
    console.print("[bold cyan]Rich-based Terminal UI Demo[/bold cyan]")
    console.print("[dim]Simulating sensor data updates...[/dim]")
    console.print("[yellow]Press Ctrl+C to exit[/yellow]\n")
    
    try:
        with Live(console=console, refresh_per_second=2) as live:
            counter = 0
            while counter < 30:  # Run for 30 updates
                data = create_demo_data(counter)
                
                # Create layout
                layout = Layout()
                layout.split_column(
                    Layout(Panel(
                        "[bold]MQTT Sensor Monitor Demo[/bold]\n"
                        "[cyan]Broker:[/cyan] localhost:1883 (simulated)\n"
                        "[cyan]Topic:[/cyan] iot_logger",
                        title="Configuration",
                        border_style="blue"
                    ), size=7),
                    Layout(create_sensor_table(data, counter)),
                    Layout(Panel(
                        f"[bold]Status:[/bold] [green]✓ Running (Demo Mode)[/green]\n"
                        f"[bold]Updates:[/bold] {counter} / 30",
                        title="Info",
                        border_style="green"
                    ), size=5)
                )
                
                live.update(layout)
                counter += 1
                time.sleep(1)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo stopped[/yellow]")
    
    console.print("[green]Demo completed![/green]")
    console.print("\n[bold]Notice how the display updates cleanly without scrolling![/bold]")
    console.print("Your terminal history remains clean - scroll up to see this message again.")


if __name__ == "__main__":
    main()
