#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Terminal output streaming module for capturing and broadcasting terminal output.

This module provides a way to capture terminal output from scripts and broadcast
it to multiple consumers (like websocket clients) while maintaining independence
between the data source and consumers.
"""

import io
import sys
import threading
from typing import Callable, List, Optional


class TerminalStreamer:
    """
    Captures terminal output and broadcasts it to registered callbacks.
    
    This class can wrap stdout/stderr or capture output from functions,
    allowing scripts to work normally while also streaming their output.
    """
    
    def __init__(self):
        """Initialize the terminal streamer"""
        self._callbacks: List[Callable[[str], None]] = []
        self._lock = threading.Lock()
        self._buffer = io.StringIO()
        self._original_stdout = None
        self._original_stderr = None
        self._capturing = False
    
    def register_callback(self, callback: Callable[[str], None]) -> None:
        """
        Register a callback to receive terminal output.
        
        :param callback: Function that takes a string and handles the output
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[str], None]) -> None:
        """
        Unregister a callback.
        
        :param callback: The callback to remove
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def broadcast(self, text: str) -> None:
        """
        Broadcast text to all registered callbacks.
        
        :param text: The text to broadcast
        """
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(text)
                except Exception as e:
                    # Don't let one bad callback break others
                    print(f"Error in callback: {e}", file=sys.stderr)
    
    def write(self, text: str) -> None:
        """
        Write text to both the original stdout and broadcast to callbacks.
        This method makes TerminalStreamer compatible with file-like objects.
        
        :param text: The text to write
        """
        # Write to original stdout if we're capturing
        if self._original_stdout is not None:
            self._original_stdout.write(text)
            self._original_stdout.flush()
        else:
            # If not capturing, write to sys.stdout
            sys.stdout.write(text)
            sys.stdout.flush()
        
        # Broadcast to callbacks
        self.broadcast(text)
    
    def flush(self) -> None:
        """Flush the output (required for file-like interface)"""
        if self._original_stdout is not None:
            self._original_stdout.flush()
        else:
            sys.stdout.flush()
    
    def start_capture(self) -> None:
        """
        Start capturing stdout and stderr.
        All print() calls will be broadcast to registered callbacks.
        """
        if self._capturing:
            return
        
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        self._capturing = True
    
    def stop_capture(self) -> None:
        """Stop capturing stdout and stderr"""
        if not self._capturing:
            return
        
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        self._original_stdout = None
        self._original_stderr = None
        self._capturing = False


class TerminalOutputCapture:
    """
    Context manager for capturing terminal output without modifying global stdout.
    This is useful when you want to capture output from a specific code block.
    """
    
    def __init__(self, streamer: TerminalStreamer):
        """
        Initialize the capture context.
        
        :param streamer: The TerminalStreamer instance to use
        """
        self.streamer = streamer
        self.original_stdout = None
        self.original_stderr = None
    
    def __enter__(self):
        """Start capturing"""
        self.streamer.start_capture()
        return self.streamer
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing"""
        self.streamer.stop_capture()
        return False
