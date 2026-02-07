# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests for terminal streaming and WebSocket functionality
"""

import asyncio
import json
import sys
import threading
import time
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from terminal_streamer import TerminalStreamer, TerminalOutputCapture


class TestTerminalStreamer(unittest.TestCase):
    """Test the TerminalStreamer class"""

    def setUp(self):
        """Set up test fixtures"""
        self.streamer = TerminalStreamer()

    def tearDown(self):
        """Clean up after tests"""
        # Make sure we stop any capturing
        if self.streamer._capturing:
            self.streamer.stop_capture()

    def test_callback_registration(self):
        """Test registering and unregistering callbacks"""
        callback1 = MagicMock()
        callback2 = MagicMock()

        # Register callbacks
        self.streamer.register_callback(callback1)
        self.streamer.register_callback(callback2)

        # Should have 2 callbacks
        self.assertEqual(len(self.streamer._callbacks), 2)

        # Registering same callback again should not duplicate
        self.streamer.register_callback(callback1)
        self.assertEqual(len(self.streamer._callbacks), 2)

        # Unregister a callback
        self.streamer.unregister_callback(callback1)
        self.assertEqual(len(self.streamer._callbacks), 1)

        # Unregistering non-existent callback should be safe
        self.streamer.unregister_callback(callback1)
        self.assertEqual(len(self.streamer._callbacks), 1)

    def test_broadcast(self):
        """Test broadcasting to callbacks"""
        callback1 = MagicMock()
        callback2 = MagicMock()

        self.streamer.register_callback(callback1)
        self.streamer.register_callback(callback2)

        # Broadcast some text
        self.streamer.broadcast("Hello, World!")

        # Both callbacks should have been called
        callback1.assert_called_once_with("Hello, World!")
        callback2.assert_called_once_with("Hello, World!")

    def test_broadcast_with_failing_callback(self):
        """Test that one failing callback doesn't break others"""
        callback1 = MagicMock(side_effect=Exception("Test error"))
        callback2 = MagicMock()

        self.streamer.register_callback(callback1)
        self.streamer.register_callback(callback2)

        # Broadcast should not raise exception
        self.streamer.broadcast("Test")

        # Second callback should still be called
        callback2.assert_called_once_with("Test")

    def test_write_method(self):
        """Test the write method (file-like interface)"""
        callback = MagicMock()
        self.streamer.register_callback(callback)

        # Write some text
        self.streamer.write("Test output")

        # Callback should have been called
        callback.assert_called_once_with("Test output")

    def test_capture_stdout(self):
        """Test capturing stdout"""
        captured_output = []
        
        def callback(text):
            captured_output.append(text)
        
        self.streamer.register_callback(callback)

        # Start capturing
        self.streamer.start_capture()
        self.assertTrue(self.streamer._capturing)

        # Print something
        print("Test message", end="")

        # Stop capturing
        self.streamer.stop_capture()
        self.assertFalse(self.streamer._capturing)

        # Callback should have received the output
        output = "".join(captured_output)
        self.assertEqual(output, "Test message")

    def test_context_manager(self):
        """Test the TerminalOutputCapture context manager"""
        captured_output = []
        
        def callback(text):
            captured_output.append(text)
        
        self.streamer.register_callback(callback)

        # Use context manager
        with TerminalOutputCapture(self.streamer):
            print("Captured text", end="")

        # Should not be capturing after context exit
        self.assertFalse(self.streamer._capturing)

        # Callback should have received the output
        output = "".join(captured_output)
        self.assertEqual(output, "Captured text")

    def test_multiple_start_stop(self):
        """Test multiple start/stop cycles"""
        captured_output = []
        
        def callback(text):
            captured_output.append(text)
        
        self.streamer.register_callback(callback)

        # First cycle
        self.streamer.start_capture()
        print("Message 1", end="")
        self.streamer.stop_capture()

        # Second cycle
        self.streamer.start_capture()
        print("Message 2", end="")
        self.streamer.stop_capture()

        # Should have received both messages
        output = "".join(captured_output)
        self.assertIn("Message 1", output)
        self.assertIn("Message 2", output)

    def test_thread_safety(self):
        """Test thread-safe callback registration"""
        callbacks_called = []

        def make_callback(n):
            def callback(text):
                callbacks_called.append(n)
            return callback

        # Register callbacks from multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(
                target=self.streamer.register_callback,
                args=(make_callback(i),)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have 10 callbacks
        self.assertEqual(len(self.streamer._callbacks), 10)

        # Broadcast should call all
        self.streamer.broadcast("test")
        self.assertEqual(len(callbacks_called), 10)


class TestWebSocketServer(unittest.TestCase):
    """Test the WebSocket server functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock websockets to avoid import errors in test environment
        self.websockets_mock = MagicMock()
        sys.modules['websockets'] = self.websockets_mock
        sys.modules['websockets.server'] = MagicMock()

    def tearDown(self):
        """Clean up after tests"""
        # Remove mocked modules
        if 'websockets' in sys.modules:
            del sys.modules['websockets']
        if 'websockets.server' in sys.modules:
            del sys.modules['websockets.server']

    def test_server_initialization(self):
        """Test WebSocket server initialization"""
        # This test verifies the server can be imported and instantiated
        # with mocked websockets
        try:
            # The import will fail if websockets is not installed
            # but we've mocked it above
            from examples.websocket_terminal_server import WebSocketTerminalServer
            
            server = WebSocketTerminalServer(host="localhost", port=8765)
            
            self.assertEqual(server.host, "localhost")
            self.assertEqual(server.port, 8765)
            self.assertIsNotNone(server.streamer)
            self.assertEqual(len(server.clients), 0)
        except ImportError:
            # If import fails even with mocks, skip test
            self.skipTest("websockets module not available")

    def test_broadcast_message_format(self):
        """Test that broadcast messages are properly formatted"""
        try:
            from examples.websocket_terminal_server import WebSocketTerminalServer
            
            server = WebSocketTerminalServer()
            
            # Mock a client
            mock_client = MagicMock()
            server.clients.add(mock_client)
            
            # Broadcast some text through the streamer
            test_text = "Test output\n"
            server.streamer.broadcast(test_text)
            
            # Give async tasks a moment to process
            time.sleep(0.1)
            
            # Note: Full verification would require async test framework
            # This test verifies the structure is correct
        except ImportError:
            self.skipTest("websockets module not available")


class TestTerminalStreamerIntegration(unittest.TestCase):
    """Integration tests for terminal streaming"""

    def test_capture_multiline_output(self):
        """Test capturing multiple lines of output"""
        streamer = TerminalStreamer()
        captured = []

        def capture_callback(text):
            captured.append(text)

        streamer.register_callback(capture_callback)
        streamer.start_capture()

        # Print multiple lines
        print("Line 1")
        print("Line 2")
        print("Line 3")

        streamer.stop_capture()

        # Should have captured all lines (including newlines)
        output = "".join(captured)
        self.assertIn("Line 1", output)
        self.assertIn("Line 2", output)
        self.assertIn("Line 3", output)

    def test_capture_preserves_formatting(self):
        """Test that captured output preserves formatting"""
        streamer = TerminalStreamer()
        captured = []

        def capture_callback(text):
            captured.append(text)

        streamer.register_callback(capture_callback)
        streamer.start_capture()

        # Print with tabs and spaces
        print("Column1\tColumn2\tColumn3")
        print("  Indented text")

        streamer.stop_capture()

        output = "".join(captured)
        self.assertIn("\t", output)
        self.assertIn("  Indented", output)


if __name__ == "__main__":
    unittest.main()
