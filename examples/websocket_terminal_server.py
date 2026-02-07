#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
WebSocket server for streaming terminal output to web clients.

This server broadcasts terminal output from MQTT sensor examples to connected
web clients via WebSocket, maintaining the terminal charm and formatting.
"""

import argparse
import asyncio
import json
import sys
import threading
from pathlib import Path
from typing import Set

try:
    import websockets
    from websockets.server import serve
except ImportError:
    print("\n" + "=" * 60)
    print("ERROR: websockets library not installed")
    print("=" * 60)
    print("\nThis server requires the websockets library.")
    print("\nTo install websockets, run:")
    print("    pip install websockets")
    print("\nOr install all optional dependencies:")
    print("    pip install -r optional_requirements.txt")
    print("=" * 60 + "\n")
    sys.exit(1)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from terminal_streamer import TerminalStreamer


class WebSocketTerminalServer:
    """WebSocket server that broadcasts terminal output to connected clients"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Initialize the WebSocket server.
        
        :param host: Host address to bind to
        :param port: Port to listen on
        """
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.streamer = TerminalStreamer()
        self.streamer.register_callback(self._broadcast_to_clients)
        self._broadcast_lock = asyncio.Lock()
    
    def _broadcast_to_clients(self, text: str) -> None:
        """
        Broadcast text to all connected WebSocket clients.
        This is called from the terminal streamer callback.
        
        :param text: Text to broadcast
        """
        if not self.clients:
            return
        
        # Create a message with the text
        message = json.dumps({
            "type": "output",
            "data": text
        })
        
        # Schedule broadcast in the event loop
        # We need to handle this carefully since we might be called from a different thread
        try:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(self._async_broadcast(message), loop)
        except RuntimeError:
            # No event loop in current thread, this is expected
            pass
    
    async def _async_broadcast(self, message: str) -> None:
        """
        Asynchronously broadcast a message to all clients.
        
        :param message: The message to broadcast
        """
        if not self.clients:
            return
        
        # Create a copy of clients to avoid modification during iteration
        clients = self.clients.copy()
        
        # Broadcast to all clients
        await asyncio.gather(
            *[self._send_to_client(client, message) for client in clients],
            return_exceptions=True
        )
    
    async def _send_to_client(self, client, message: str) -> None:
        """
        Send a message to a single client.
        
        :param client: The WebSocket client
        :param message: The message to send
        """
        try:
            await client.send(message)
        except Exception:
            # Client disconnected or error, will be handled in handler
            pass
    
    async def handler(self, websocket) -> None:
        """
        Handle a WebSocket connection.
        
        :param websocket: The WebSocket connection
        """
        # Register client
        self.clients.add(websocket)
        print(
            f"Client connected from {websocket.remote_address}. "
            f"Total clients: {len(self.clients)}"
        )
        
        try:
            # Send welcome message
            welcome = json.dumps({
                "type": "info",
                "data": "Connected to MQTT Terminal Streamer"
            })
            await websocket.send(welcome)
            
            # Keep connection alive and handle incoming messages
            async for message in websocket:
                # Handle client messages if needed (e.g., commands)
                try:
                    data = json.loads(message)
                    if data.get("type") == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Unregister client
            self.clients.remove(websocket)
            print(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def start_server(self) -> None:
        """Start the WebSocket server"""
        async with serve(self.handler, self.host, self.port):
            print(f"WebSocket server started on ws://{self.host}:{self.port}")
            print(f"Open the web UI in your browser to view the terminal output")
            print("Press Ctrl+C to stop the server")
            # Keep running forever
            await asyncio.Future()  # run forever
    
    def run_sensor_script(self, script_func, *args, **kwargs) -> None:
        """
        Run a sensor script in a separate thread with output capture.
        
        :param script_func: The function to run (e.g., main() from a sensor example)
        :param args: Positional arguments to pass to the function
        :param kwargs: Keyword arguments to pass to the function
        """
        def run_with_capture():
            """Run the script with terminal capture"""
            self.streamer.start_capture()
            try:
                script_func(*args, **kwargs)
            finally:
                self.streamer.stop_capture()
        
        # Run in a separate thread
        thread = threading.Thread(target=run_with_capture, daemon=True)
        thread.start()


async def main_async(args):
    """Async main function"""
    # Import modules here based on script type to avoid import errors
    # when optional dependencies are not installed
    # noqa: PLC0415 - Import inside function for optional dependencies
    if args.script == "basic":
        from examples import mqtt_sensor_example  # noqa: PLC0415
        script_main = mqtt_sensor_example.main
    elif args.script == "rich":
        from examples import mqtt_sensor_example_rich  # noqa: PLC0415
        script_main = mqtt_sensor_example_rich.main
    elif args.script == "textual":
        print("Warning: Textual UI may not work well with WebSocket streaming")
        print("Consider using 'basic' or 'rich' script types instead")
        from examples import mqtt_sensor_example_textual  # noqa: PLC0415
        script_main = mqtt_sensor_example_textual.main
    else:
        raise ValueError(f"Unknown script type: {args.script}")
    
    server = WebSocketTerminalServer(host=args.host, port=args.port)
    server.run_sensor_script(script_main)
    
    # Start the WebSocket server
    await server.start_server()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="WebSocket server for streaming MQTT terminal output to web browsers"
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
    parser.add_argument(
        "--script",
        choices=["basic", "rich", "textual"],
        default="basic",
        help="Which MQTT example script to run (default: basic)"
    )
    parser.add_argument(
        "--mqtt-host",
        default="localhost",
        help="MQTT broker hostname (default: localhost)"
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--mqtt-topic",
        default="iot_logger",
        help="MQTT topic to subscribe to (default: iot_logger)"
    )
    
    args = parser.parse_args()
    
    # Store MQTT args for the script to use
    # Note: This is a simple approach; a better architecture would pass these through
    sys.argv = [
        sys.argv[0],
        "--host", args.mqtt_host,
        "--port", str(args.mqtt_port),
        "--topic", args.mqtt_topic,
    ]
    
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        print("Goodbye!")


if __name__ == "__main__":
    main()
