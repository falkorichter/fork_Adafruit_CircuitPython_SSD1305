# SPDX-FileCopyrightText: 2025 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Display timeout management for OLED burn-in prevention.

This module provides keyboard activity monitoring and display timeout
functionality to prevent OLED burn-in. It supports multiple input
detection methods for different environments.

Usage:
    from display_timeout import DisplayTimeoutManager, keyboard_listener
    import threading
    
    # Create timeout manager
    timeout_manager = DisplayTimeoutManager(timeout_seconds=10.0, enabled=True)
    
    # Start keyboard monitoring in background thread
    keyboard_thread = threading.Thread(
        target=keyboard_listener, 
        args=(timeout_manager, "auto"),  # method: auto, pynput, evdev, file, or stdin
        daemon=True
    )
    keyboard_thread.start()
    
    # In your main loop
    while True:
        if timeout_manager.should_display_be_active():
            # Update display with content
            display.show()
        else:
            # Blank display to prevent burn-in
            display.clear()

Input Detection Methods:
    - pynput: Cross-platform keyboard monitoring (requires X11/display server)
    - evdev: Linux /dev/input monitoring (works in headless environments)
    - file: File timestamp monitoring (universal fallback)
    - stdin: Terminal input monitoring (interactive only)
    - auto: Try all methods in order until one works (default)

Dependencies:
    - pynput (optional): pip install pynput
    - evdev (optional): pip install evdev
"""

import logging
import sys
import threading
import time

# Get logger for this module
logger = logging.getLogger(__name__)


class DisplayTimeoutManager:
    """Manages display timeout for burn-in prevention"""

    def __init__(self, timeout_seconds=10.0, enabled=True):
        """
        Initialize the timeout manager

        :param timeout_seconds: Seconds of inactivity before blanking display
        :param enabled: Whether timeout feature is enabled
        """
        self.timeout_seconds = timeout_seconds
        self.enabled = enabled
        self.last_activity_time = time.time()
        self._display_active = True
        self._lock = threading.Lock()

    def register_activity(self):
        """Called when keyboard activity is detected"""
        with self._lock:
            self.last_activity_time = time.time()
            was_inactive = not self._display_active
            self._display_active = True
            return was_inactive  # Return True if display was off and should be re-activated

    def should_display_be_active(self):
        """
        Check if display should be active based on timeout

        :return: True if display should be active, False if it should be blanked
        """
        if not self.enabled:
            return True

        with self._lock:
            elapsed = time.time() - self.last_activity_time
            should_be_active = elapsed < self.timeout_seconds

            # Update internal state
            self._display_active = should_be_active

            return should_be_active

    @property
    def display_active(self):
        """Get current display active state"""
        with self._lock:
            return self._display_active


def pynput_listener(timeout_manager):
    """
    Monitor keyboard activity using pynput (Option A)
    Works on systems with X11/display server

    :param timeout_manager: DisplayTimeoutManager instance to update on activity
    """
    try:
        from pynput import keyboard  # noqa: PLC0415

        def on_press(key):
            """Called when any key is pressed"""
            # Log the keystroke for debugging
            try:
                key_name = key.char if (hasattr(key, 'char') and key.char) else str(key)
            except AttributeError:
                key_name = str(key)
            logger.debug(f"Key pressed (pynput): {key_name}")

            was_inactive = timeout_manager.register_activity()
            if was_inactive:
                logger.info(f"Display reactivated by keyboard input (pynput): {key_name}")

        # Start listening to keyboard events
        logger.info("Starting pynput keyboard listener...")
        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        # Check if listener started successfully
        time.sleep(0.5)
        if not listener.running:
            logger.warning("pynput listener failed to start (may need X11/display server)")
            listener.stop()
            return False

        logger.info("pynput keyboard listener active")
        listener.join()
        return True

    except ImportError:
        logger.warning("pynput library not available. Install with: pip install pynput")
        return False
    except Exception as e:
        logger.warning(f"pynput keyboard monitoring failed: {e}")
        return False


def _is_keyboard_device(device):
    """Check if an evdev device is a keyboard"""
    caps = device.capabilities(verbose=False)
    # Check if device has key event capability (EV_KEY = 1)
    if 1 not in caps:
        return False
    # Check if it has actual keyboard keys (not just power button, etc.)
    keys = caps[1]
    # Look for common keyboard keys (A-Z range is 30-38, etc.)
    return any(k in range(1, 128) for k in keys)


def _get_key_name(evdev, event_code):
    """Get human-readable key name from evdev event code"""
    if event_code in evdev.ecodes.KEY:
        return evdev.ecodes.KEY[event_code]
    return f"code:{event_code}"


def _find_keyboard_devices(evdev):
    """Find all keyboard devices using evdev"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    keyboards = []
    for device in devices:
        if _is_keyboard_device(device):
            keyboards.append(device)
            logger.info(f"Found keyboard device: {device.name} ({device.path})")
    return keyboards


def evdev_listener(timeout_manager):
    """
    Monitor keyboard activity using evdev (Option B)
    Works on Linux systems, reads from /dev/input/event*

    :param timeout_manager: DisplayTimeoutManager instance to update on activity
    """
    try:
        import select  # noqa: PLC0415

        import evdev  # noqa: PLC0415

        logger.info("Starting evdev keyboard listener...")

        keyboards = _find_keyboard_devices(evdev)
        if not keyboards:
            logger.warning("No keyboard devices found via evdev")
            return False

        logger.info(f"Monitoring {len(keyboards)} keyboard device(s) via evdev")

        # Monitor all keyboard devices
        while True:
            # Use select to wait for events from any keyboard
            r, w, x = select.select(keyboards, [], [], 0.5)
            for device in r:
                try:
                    # Read events
                    for event in device.read():
                        # Key event (EV_KEY)
                        if event.type == evdev.ecodes.EV_KEY:
                            # Extract key name once to avoid redundant calls
                            key_name = _get_key_name(evdev, event.code)

                            # Log both press and release for debugging
                            if event.value in {0, 1}:
                                logger.debug(
                                    f"Key {'pressed' if event.value == 1 else 'released'} "
                                    f"(evdev): {key_name}"
                                )

                            # Only register activity on key press (value=1)
                            if event.value == 1:
                                was_inactive = timeout_manager.register_activity()
                                if was_inactive:
                                    logger.info(
                                        f"Display reactivated by keyboard input "
                                        f"(evdev: {device.name}, key: {key_name})"
                                    )
                                # Continue to process other events
                except OSError:
                    # Device disconnected
                    pass

    except ImportError:
        logger.warning("evdev library not available. Install with: pip install evdev")
        return False
    except PermissionError:
        logger.error("Permission denied accessing /dev/input devices.")
        logger.error("Try running with sudo or add user to 'input' group:")
        logger.error("  sudo usermod -a -G input $USER")
        return False
    except Exception as e:
        logger.warning(f"evdev keyboard monitoring failed: {e}")
        return False


def _check_input_device_activity(input_dir, last_check_time, timeout_manager):
    """Check if any input device has been accessed since last check"""
    for device_file in input_dir.glob("event*"):
        try:
            stat = device_file.stat()
            # Check if file was accessed after our last check
            if stat.st_atime > last_check_time or stat.st_mtime > last_check_time:
                # Log the activity for debugging
                logger.debug(f"Input device activity detected (file timestamp): {device_file.name}")

                was_inactive = timeout_manager.register_activity()
                if was_inactive:
                    logger.info(
                        f"Display reactivated by input activity "
                        f"(file timestamp: {device_file.name})"
                    )
                # Activity detected, no need to continue checking
                return
        except (OSError, PermissionError):
            # Skip files we can't access
            pass


def file_timestamp_listener(timeout_manager):
    """
    Monitor keyboard activity via file timestamps (Option C)
    Universal fallback that works on most systems

    :param timeout_manager: DisplayTimeoutManager instance to update on activity
    """
    logger.info("Starting file timestamp monitoring...")
    logger.info("Monitoring /dev/input for device activity")

    from pathlib import Path  # noqa: PLC0415

    input_dir = Path("/dev/input")

    if not input_dir.exists():
        logger.error("/dev/input directory not found - cannot monitor keyboard activity")
        return False

    logger.info("File timestamp monitoring active")

    # Track last modification times
    last_check_time = time.time()

    while True:
        try:
            current_time = time.time()
            _check_input_device_activity(input_dir, last_check_time, timeout_manager)
            last_check_time = current_time
            time.sleep(0.5)  # Check every 0.5 seconds

        except Exception as e:
            logger.error(f"File timestamp monitoring error: {e}")
            return False


def stdin_listener(timeout_manager):
    """
    Monitor keyboard activity via stdin (Option D - terminal fallback)
    Only works when running interactively in a terminal

    :param timeout_manager: DisplayTimeoutManager instance to update on activity
    """
    logger.info("Starting stdin activity monitoring")
    logger.info("Any keyboard input in this terminal will reset the timeout")

    try:
        import select  # noqa: PLC0415

        # Monitor stdin for activity
        while True:
            # Check if there's input available on stdin (non-blocking)
            readable, _, _ = select.select([sys.stdin], [], [], 0.5)
            if readable:
                # Drain the input buffer
                try:
                    data = sys.stdin.read(1024)
                    # Log the input for debugging (sanitize for logging)
                    logger.debug(f"Stdin input detected: {len(data)} character(s)")
                except OSError:
                    pass
                was_inactive = timeout_manager.register_activity()
                if was_inactive:
                    logger.info("Display reactivated by keyboard input (stdin)")

    except Exception as e:
        logger.error(f"Stdin monitoring failed: {e}")
        return False


def keyboard_listener(timeout_manager, method="auto"):
    """
    Background thread to monitor keyboard activity

    :param timeout_manager: DisplayTimeoutManager instance to update on activity
    :param method: Input detection method: 'auto', 'pynput', 'evdev', 'file', or 'stdin'
    """
    if method == "pynput":
        logger.info("Using pynput method (manual selection)")
        if not pynput_listener(timeout_manager):
            logger.error("pynput method failed and no fallback allowed")
            return

    elif method == "evdev":
        logger.info("Using evdev method (manual selection)")
        if not evdev_listener(timeout_manager):
            logger.error("evdev method failed and no fallback allowed")
            return

    elif method == "file":
        logger.info("Using file timestamp method (manual selection)")
        if not file_timestamp_listener(timeout_manager):
            logger.error("file timestamp method failed and no fallback allowed")
            return

    elif method == "stdin":
        logger.info("Using stdin method (manual selection)")
        if not stdin_listener(timeout_manager):
            logger.error("stdin method failed and no fallback allowed")
            return

    else:  # auto
        logger.info("Auto-detecting best input monitoring method...")

        # Try methods in order of preference
        if not pynput_listener(timeout_manager):
            logger.info("Trying evdev method...")
            if not evdev_listener(timeout_manager):
                logger.info("Trying file timestamp method...")
                if not file_timestamp_listener(timeout_manager):
                    logger.info("Trying stdin method as last resort...")
                    if not stdin_listener(timeout_manager):
                        logger.error("All input monitoring methods failed!")
                        logger.error("Display timeout feature disabled.")
