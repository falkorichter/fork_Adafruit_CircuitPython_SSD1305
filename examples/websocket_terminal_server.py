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
import os
import sys
import threading
import traceback
from pathlib import Path
from typing import Set

try:
    import websockets
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

# Add repository root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from terminal_streamer import TerminalStreamer


class WebSocketTerminalServer:
    """WebSocket server that broadcasts terminal output to connected clients"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, debug: bool = False):
        """
        Initialize the WebSocket server.
        
        :param host: Host address to bind to
        :param port: Port to listen on
        :param debug: Enable debug output
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.streamer = TerminalStreamer()
        self.streamer.register_callback(self._broadcast_to_clients)
        self._broadcast_lock = asyncio.Lock()
        self.loop = None  # Will be set when server starts
        self._broadcast_count = 0  # Track number of broadcasts
    
    def _broadcast_to_clients(self, text: str) -> None:
        """
        Broadcast text to all connected WebSocket clients.
        This is called from the terminal streamer callback.
        
        :param text: Text to broadcast
        """
        def debug_print(msg):
            """Print debug message bypassing capture"""
            if self.debug:
                # Write to original stderr to bypass capture
                if self.streamer._original_stderr:
                    self.streamer._original_stderr.write(msg + '\n')
                    self.streamer._original_stderr.flush()
                else:
                    print(msg, file=sys.stderr)
        
        if not self.clients or not self.loop:
            if not self.clients:
                debug_print("[DEBUG] No clients connected, skipping broadcast")
            elif not self.loop:
                debug_print("[DEBUG] Event loop not set, skipping broadcast")
            return
        
        self._broadcast_count += 1
        if self.debug:
            debug_print(
                f"[DEBUG] Broadcasting #{self._broadcast_count}: "
                f"{len(text)} chars to {len(self.clients)} client(s)"
            )
            if len(text) < 100:
                debug_print(f"[DEBUG] Content: {repr(text)}")
        
        # Create a message with the text
        message = json.dumps({
            "type": "output",
            "data": text
        })
        
        # Schedule broadcast in the event loop from another thread
        asyncio.run_coroutine_threadsafe(self._async_broadcast(message), self.loop)
    
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
        # Store the event loop for cross-thread communication
        self.loop = asyncio.get_running_loop()
        
        async with websockets.serve(self.handler, self.host, self.port):
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
        def debug_print(msg):
            """Print debug message bypassing capture by writing to original stderr"""
            if self.debug:
                # Write to original stderr if capture is active, otherwise use sys.stderr
                if self.streamer._original_stderr:
                    self.streamer._original_stderr.write(msg + '\n')
                    self.streamer._original_stderr.flush()
                else:
                    print(msg, file=sys.stderr)
        
        def run_with_capture():
            """Run the script with terminal capture"""
            debug_print(
                f"[DEBUG] Starting sensor script: "
                f"{script_func.__module__}.{script_func.__name__}"
            )
            debug_print(f"[DEBUG] Capture enabled: {self.streamer is not None}")
            
            self.streamer.start_capture()
            try:
                debug_print("[DEBUG] Running sensor script...")
                script_func(*args, **kwargs)
            except Exception as e:
                debug_print(f"[ERROR] Sensor script failed: {e}")
                # For traceback, write to original stderr
                if self.streamer._original_stderr:
                    traceback.print_exc(file=self.streamer._original_stderr)
                else:
                    traceback.print_exc()
            finally:
                debug_print("[DEBUG] Stopping capture...")
                self.streamer.stop_capture()
        
        # Run in a separate thread
        thread = threading.Thread(target=run_with_capture, daemon=True)
        thread.start()
        debug_print(f"[DEBUG] Sensor script thread started (daemon={thread.daemon})")


async def main_async(args):
    """Async main function"""
    # Import modules here based on script type to avoid import errors
    # when optional dependencies are not installed
    # noqa: PLC0415 - Import inside function for optional dependencies
    if args.script == "basic":
        from examples import mqtt_sensor_example  # noqa: PLC0415
        script_main = mqtt_sensor_example.main
    elif args.script == "rich":
        print("\n" + "=" * 70)
        print("WARNING: Rich library compatibility issue with WebSocket streaming")
        print("=" * 70)
        print("The Rich library uses advanced terminal features (Live display,")
        print("alternate screen buffer) that bypass standard stdout capture.")
        print("This means Rich output may not stream properly to the browser.")
        print("\nFor WebSocket streaming, use: --script rich-streaming")
        print("For terminal-only use, run: python examples/mqtt_sensor_example_rich.py")
        print("=" * 70 + "\n")
        from examples import mqtt_sensor_example_rich  # noqa: PLC0415
        script_main = mqtt_sensor_example_rich.main
    elif args.script == "rich-streaming":
        print("\n[INFO] Using Rich streaming-compatible version")
        print("       Optimized for WebSocket streaming with periodic updates\n")
        from examples import mqtt_sensor_example_rich_streaming  # noqa: PLC0415
        script_main = mqtt_sensor_example_rich_streaming.main
    elif args.script == "textual":
        print("\n" + "=" * 70)
        print("WARNING: Textual UI compatibility issue with WebSocket streaming")
        print("=" * 70)
        print("Textual uses alternate screen buffers and direct terminal access")
        print("that cannot be captured via stdout redirection.")
        print("\nFor best WebSocket streaming experience, use: --script basic")
        print("=" * 70 + "\n")
        from examples import mqtt_sensor_example_textual  # noqa: PLC0415
        script_main = mqtt_sensor_example_textual.main
    else:
        raise ValueError(f"Unknown script type: {args.script}")
    
    server = WebSocketTerminalServer(
        host=args.ws_host,
        port=args.ws_port,
        debug=args.debug
    )
    server.run_sensor_script(script_main)
    
    # Start the WebSocket server
    await server.start_server()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="WebSocket server for streaming MQTT terminal output to web browsers"
    )
    parser.add_argument(
        "--ws-host",
        default="0.0.0.0",
        help="WebSocket server bind address - use 0.0.0.0 for all interfaces, "
             "localhost for local only (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--ws-port",
        type=int,
        default=8765,
        help="WebSocket server port (default: 8765)"
    )
    parser.add_argument(
        "--script",
        choices=["basic", "rich", "rich-streaming", "textual"],
        default="basic",
        help="Which MQTT example script to run (default: basic). "
             "Use 'rich-streaming' for Rich UI compatible with WebSocket streaming."
    )
    parser.add_argument(
        "--mqtt-host",
        default="localhost",
        help="MQTT broker hostname or IP address to connect to (default: localhost)"
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output for troubleshooting"
    )
    
    args = parser.parse_args()
    
    # Enable debug mode if requested
    if args.debug:
        print("[DEBUG] Debug mode enabled", file=sys.stderr)
        os.environ['WEBSOCKET_DEBUG'] = '1'
    
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
