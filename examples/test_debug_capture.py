#!/usr/bin/env python3
# Test that debug messages don't get captured and sent to WebSocket clients

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from terminal_streamer import TerminalStreamer

# Test that writing to original stderr bypasses capture
streamer = TerminalStreamer()
captured_output = []

def capture_callback(text):
    captured_output.append(text)

streamer.register_callback(capture_callback)

print("Before capture - should NOT be captured")

streamer.start_capture()

print("This should be captured")

# This simulates what debug_print() does in websocket_terminal_server.py
if streamer._original_stderr:
    streamer._original_stderr.write("DEBUG message (should NOT be captured)\n")
    streamer._original_stderr.flush()

print("Another captured message")

streamer.stop_capture()

print("After capture - should NOT be captured")

print("\n=== Results ===")
print(f"Captured {len(captured_output)} items:")
for i, item in enumerate(captured_output):
    print(f"  {i+1}. {repr(item)}")

# Verify - the print() calls each create a newline, so we get 4 items total
assert len(captured_output) == 4, f"Expected 4 items, got {len(captured_output)}"
assert "This should be captured" in captured_output[0], f"Expected stdout to be captured"
assert "Another captured message" in captured_output[2], f"Expected stdout to be captured"
assert all("DEBUG" not in str(item) for item in captured_output), "DEBUG messages should NOT be captured"

print("\n✓ Test passed: debug messages written to original_stderr are not captured")
