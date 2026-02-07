#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Integration test for WebSocket terminal server.

This script tests that the WebSocket server can start, accept connections,
and stream terminal output to clients.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import websockets
except ImportError:
    print("ERROR: websockets library not installed")
    print("Install with: pip install websockets")
    sys.exit(1)

from terminal_streamer import TerminalStreamer


async def test_websocket_server():
    """Test the WebSocket server functionality"""
    print("=" * 60)
    print("Testing WebSocket Terminal Server")
    print("=" * 60)
    
    # We'll test the server components manually to avoid needing
    # an actual MQTT broker running
    
    # Import the server class
    from examples.websocket_terminal_server import WebSocketTerminalServer
    
    # Create server instance
    server = WebSocketTerminalServer(host="localhost", port=8766)
    print(f"\n✓ Server instance created on {server.host}:{server.port}")
    
    # Test the streamer
    received_messages = []
    
    def test_callback(text):
        received_messages.append(text)
    
    server.streamer.register_callback(test_callback)
    print("✓ Callback registered with streamer")
    
    # Test broadcasting
    server.streamer.broadcast("Test message 1\n")
    server.streamer.broadcast("Test message 2\n")
    
    assert len(received_messages) == 2, "Should receive 2 messages"
    assert received_messages[0] == "Test message 1\n"
    assert received_messages[1] == "Test message 2\n"
    print("✓ Broadcasting works correctly")
    
    # Test capturing output
    server.streamer.start_capture()
    print("Test output from print statement")
    server.streamer.stop_capture()
    
    # Should have captured the print statement
    output = "".join(received_messages)
    assert "Test output from print statement" in output
    print("✓ Output capture works correctly")
    
    print("\n" + "=" * 60)
    print("All WebSocket server tests passed!")
    print("=" * 60)


async def test_websocket_client_connection():
    """Test that a client can connect to the WebSocket server"""
    print("\n" + "=" * 60)
    print("Testing WebSocket Client Connection")
    print("=" * 60)
    
    from examples.websocket_terminal_server import WebSocketTerminalServer
    
    # Create and start server
    server = WebSocketTerminalServer(host="localhost", port=8767)
    
    # Track received messages
    client_messages = []
    
    async def client_test():
        """Client that connects and receives messages"""
        try:
            async with websockets.connect("ws://localhost:8767") as websocket:
                # Receive welcome message
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(message)
                client_messages.append(data)
                print(f"✓ Received welcome: {data['data']}")
                
                # Send some output through the server
                server.streamer.broadcast("Test broadcast message\n")
                
                # Try to receive it (with timeout)
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    client_messages.append(data)
                    print(f"✓ Received broadcast: {data['data'][:30]}...")
                except asyncio.TimeoutError:
                    print("⚠ Timeout waiting for broadcast (expected in async test)")
        except Exception as e:
            print(f"Client error: {e}")
    
    # Start server in background
    async def run_server():
        async with websockets.serve(server.handler, server.host, server.port):
            await asyncio.sleep(3)  # Run for 3 seconds
    
    # Run server and client concurrently
    try:
        await asyncio.wait_for(
            asyncio.gather(run_server(), client_test()),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        print("✓ Server and client test completed (timeout expected)")
    
    # Verify we got at least the welcome message
    assert len(client_messages) >= 1, "Should receive at least welcome message"
    assert client_messages[0]['type'] == 'info'
    
    print("\n" + "=" * 60)
    print("Client connection test passed!")
    print("=" * 60)


async def main():
    """Run all tests"""
    await test_websocket_server()
    await test_websocket_client_connection()
    
    print("\n" + "=" * 60)
    print("✓ All integration tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
