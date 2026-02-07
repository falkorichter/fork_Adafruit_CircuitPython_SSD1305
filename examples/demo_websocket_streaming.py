#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Demo script showing WebSocket terminal streaming with simulated MQTT data.

This script demonstrates the complete WebSocket terminal streaming flow
without requiring an actual MQTT broker. It simulates sensor data and
streams the terminal output to connected web clients.

Usage:
    1. Run this script:
       python examples/demo_websocket_streaming.py

    2. Open examples/websocket_terminal_viewer.html in your browser

    3. Watch the simulated sensor data stream in your browser!
"""

import argparse
import asyncio
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import websockets
except ImportError:
    print("\n" + "=" * 60)
    print("ERROR: websockets library not installed")
    print("=" * 60)
    print("\nThis demo requires the websockets library.")
    print("\nTo install websockets, run:")
    print("    pip install websockets")
    print("\nOr install all optional dependencies:")
    print("    pip install -r optional_requirements.txt")
    print("=" * 60 + "\n")
    sys.exit(1)

from terminal_streamer import TerminalStreamer


class SimulatedMQTTSensorDisplay:
    """Simulates the MQTT sensor example with fake data"""
    
    def __init__(self, streamer=None):
        """
        Initialize the simulated sensor display.
        
        :param streamer: Optional TerminalStreamer to capture output
        """
        self.streamer = streamer
        self.running = True
        
        # ANSI escape codes for terminal control
        self.CLEAR_SCREEN = "\033[2J"
        self.HOME_CURSOR = "\033[H"
    
    def generate_fake_data(self, iteration):
        """Generate fake sensor data"""
        return {
            "temperature": 22.0 + (iteration % 5) * 0.5,
            "humidity": 45.0 + (iteration % 10) * 2,
            "pressure": 101325,
            "gas_resistance": 50000 + (iteration % 20) * 100,
            "air_quality": ["Excellent", "Good", "Fair"][iteration % 3],
            "light": 500 + (iteration % 15) * 50,
            "temp_c": 22.0 + (iteration % 4) * 0.3,
            "presence_value": 800 + (iteration % 10) * 50,
            "motion_value": iteration % 5,
            "sths34_temperature": 22.0 + (iteration % 3) * 0.2,
            "person_detected": (iteration % 7) < 2,
            "voltage": 3.7 + (iteration % 5) * 0.05,
            "soc": 85 - (iteration % 20),
            "ssid": "TestNetwork",
            "rssi": -45 - (iteration % 10),
        }
    
    def print_header(self):
        """Print the static header information"""
        print("MQTT Virtual Sensor Plugin Example (Simulated)")
        print("=" * 50)
        print("WebSocket streaming enabled!")
        print("Open websocket_terminal_viewer.html in your browser")
        print("\n" + "=" * 50)
        print("Reading simulated sensor data (Ctrl+C to exit)...")
        print()
    
    def display_sensor_data(self, data):
        """Display sensor data in terminal format"""
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        # BME68x environmental data
        print(f"Temperature:    {data['temperature']:.1f} °C")
        print(f"Humidity:       {data['humidity']:.1f} %")
        print(f"Pressure:       {data['pressure']} Pa")
        print(f"Gas Resistance: {data['gas_resistance']} Ω")
        print(f"Air Quality:    {data['air_quality']}")
        
        # Other sensors
        print(f"\nLight Level:    {data['light']} lux (VEML7700)")
        print(f"Temperature:    {data['temp_c']:.1f} °C (TMP117)")
        
        # STHS34PF80 presence/motion sensor
        print(f"\nPresence:       {data['presence_value']} cm^-1 (STHS34PF80)")
        print(f"Motion:         {data['motion_value']} LSB (STHS34PF80)")
        print(f"Obj Temp:       {data['sths34_temperature']:.1f} °C (STHS34PF80)")
        
        # Person detection status
        if data['person_detected']:
            print("Person Status:  *** PERSON DETECTED ***")
        else:
            print("Person Status:  No person detected")
        
        print(f"\nBattery Voltage: {data['voltage']:.2f} V")
        print(f"Battery SOC:     {data['soc']} %")
        print(f"\nWiFi SSID:      {data['ssid']}")
        print(f"WiFi RSSI:      {data['rssi']}")
        
        print("\nStatus: Streaming via WebSocket ✓")
    
    def run(self):
        """Run the simulated sensor display"""
        if self.streamer:
            self.streamer.start_capture()
        
        try:
            # Print initial header
            self.print_header()
            
            iteration = 0
            first_iteration = True
            
            while self.running:
                # Generate fake data
                data = self.generate_fake_data(iteration)
                
                # Clear screen and redraw (skip on first iteration)
                if not first_iteration:
                    print(self.CLEAR_SCREEN + self.HOME_CURSOR, end="", flush=True)
                    self.print_header()
                first_iteration = False
                
                # Display the data
                self.display_sensor_data(data)
                
                # Wait before next update
                time.sleep(2)
                iteration += 1
                
        except KeyboardInterrupt:
            print("\n\nStopping...")
        finally:
            if self.streamer:
                self.streamer.stop_capture()
            print("Goodbye!")


class WebSocketServer:
    """Simple WebSocket server for the demo"""
    
    def __init__(self, host="localhost", port=8765):
        """Initialize the server"""
        self.host = host
        self.port = port
        self.clients = set()
        self.streamer = TerminalStreamer()
        self.streamer.register_callback(self._broadcast_to_clients)
    
    def _broadcast_to_clients(self, text):
        """Broadcast text to all WebSocket clients"""
        if not self.clients:
            return
        
        message = json.dumps({"type": "output", "data": text})
        
        try:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(self._async_broadcast(message), loop)
        except RuntimeError:
            pass
    
    async def _async_broadcast(self, message):
        """Async broadcast to all clients"""
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients.copy()],
                return_exceptions=True
            )
    
    async def handler(self, websocket):
        """Handle WebSocket connections"""
        self.clients.add(websocket)
        print(f"\n[WebSocket] Client connected. Total: {len(self.clients)}")
        
        try:
            welcome = json.dumps({
                "type": "info",
                "data": "Connected to MQTT Terminal Demo (Simulated Data)"
            })
            await websocket.send(welcome)
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"[WebSocket] Client disconnected. Total: {len(self.clients)}")
    
    async def start(self):
        """Start the WebSocket server"""
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"\n{'=' * 60}")
            print(f"WebSocket Demo Server Started")
            print(f"{'=' * 60}")
            print(f"WebSocket URL: ws://{self.host}:{self.port}")
            print(f"Web Viewer: Open websocket_terminal_viewer.html in your browser")
            print(f"{'=' * 60}\n")
            
            # Run the sensor display in the background
            sensor_display = SimulatedMQTTSensorDisplay(self.streamer)
            sensor_thread = threading.Thread(target=sensor_display.run, daemon=True)
            sensor_thread.start()
            
            # Keep the server running
            await asyncio.Future()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Demo: WebSocket terminal streaming with simulated MQTT data"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="WebSocket server host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    
    args = parser.parse_args()
    
    # Create and run the server
    server = WebSocketServer(host=args.host, port=args.port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        print("Goodbye!")


if __name__ == "__main__":
    main()
