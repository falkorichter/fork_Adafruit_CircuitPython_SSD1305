# SPDX-FileCopyrightText: <text> 2020 Tony DiCola, James DeVito,
# and 2020 Melissa LeBlanc-Williams, for Adafruit Industries </text>

# SPDX-License-Identifier: MIT


# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import argparse
import logging
import signal
import sys
import threading
import time
from pathlib import Path

import board
import busio
import digitalio
from board import D4, SCL, SDA
from PIL import Image, ImageDraw, ImageFont

import adafruit_ssd1305

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import sensor_plugins
sys.path.insert(0, str(Path(__file__).parent.parent))
from sensor_plugins import (
    BME680Plugin,
    CPULoadPlugin,
    IPAddressPlugin,
    MemoryUsagePlugin,
    TMP117Plugin,
    VEML7700Plugin,
)


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
                key_name = key.char if hasattr(key, 'char') else str(key)
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
                        # Key press event (EV_KEY, value=1 is press, value=0 is release)
                        if event.type == evdev.ecodes.EV_KEY and event.value in {0, 1}:
                            # Log the keystroke for debugging
                            key_name = evdev.ecodes.KEY[event.code] if event.code in evdev.ecodes.KEY else f"code:{event.code}"
                            logger.debug(
                                f"Key {'pressed' if event.value == 1 else 'released'} "
                                f"(evdev): {key_name}"
                            )

                            was_inactive = timeout_manager.register_activity()
                            if was_inactive:
                                logger.info(
                                    f"Display reactivated by keyboard input "
                                    f"(evdev: {device.name}, key: {key_name})"
                                )
                            break  # Only register once per batch of events
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
                return True  # Activity detected
        except (OSError, PermissionError):
            # Skip files we can't access
            pass
    return False  # No activity detected


def file_timestamp_listener(timeout_manager):
    """
    Monitor keyboard activity via file timestamps (Option C)
    Universal fallback that works on most systems

    :param timeout_manager: DisplayTimeoutManager instance to update on activity
    """
    logger.info("Starting file timestamp monitoring...")
    logger.info("Monitoring /dev/input for device activity")

    import os  # noqa: PLC0415, F401
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

    elif method == "evdev":
        logger.info("Using evdev method (manual selection)")
        if not evdev_listener(timeout_manager):
            logger.error("evdev method failed and no fallback allowed")

    elif method == "file":
        logger.info("Using file timestamp method (manual selection)")
        if not file_timestamp_listener(timeout_manager):
            logger.error("file timestamp method failed and no fallback allowed")

    elif method == "stdin":
        logger.info("Using stdin method (manual selection)")
        if not stdin_listener(timeout_manager):
            logger.error("stdin method failed and no fallback allowed")

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


# Parse command-line arguments
parser = argparse.ArgumentParser(description="SSD1305 OLED Stats Display with burn-in prevention")
parser.add_argument(
    "--blank-timeout",
    type=float,
    default=10.0,
    help="Seconds of keyboard inactivity before blanking display (default: 10.0, 0 to disable)",
)
parser.add_argument(
    "--no-blank",
    action="store_true",
    help="Disable automatic display blanking",
)
parser.add_argument(
    "--input-method",
    type=str,
    default="auto",
    choices=["auto", "pynput", "evdev", "file", "stdin"],
    help=(
        "Input detection method: auto (try all), pynput (X11), evdev (Linux), "
        "file (timestamps), stdin (terminal)"
    ),
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug logging (shows keyboard keystroke detection)",
)
args = parser.parse_args()

# Set logging level based on debug flag
if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.debug("Debug logging enabled")

# Initialize timeout manager
timeout_enabled = not args.no_blank and args.blank_timeout > 0
timeout_manager = DisplayTimeoutManager(timeout_seconds=args.blank_timeout, enabled=timeout_enabled)

# Start keyboard monitoring thread if timeout is enabled
if timeout_enabled:
    keyboard_thread = threading.Thread(
        target=keyboard_listener, args=(timeout_manager, args.input_method), daemon=True
    )
    keyboard_thread.start()
    logger.info(
        f"Display blanking enabled: {args.blank_timeout}s timeout "
        f"(method: {args.input_method})"
    )
else:
    logger.info("Display blanking disabled")

# Define the Reset Pin
oled_reset = digitalio.DigitalInOut(D4)

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

# Create the SSD1305 OLED class.
# The first two parameters are the pixel width and pixel height.  Change these
# to the right size for your display!
disp = adafruit_ssd1305.SSD1305_I2C(128, 32, i2c, reset=oled_reset)

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new("1", (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
except Exception:
    pass  # Use default font if TTF not available

# Initialize sensor plugins
tmp117 = TMP117Plugin(check_interval=5.0)
veml7700 = VEML7700Plugin(check_interval=5.0)
bme680 = BME680Plugin(check_interval=5.0, burn_in_time=300)
ip_address = IPAddressPlugin(check_interval=30.0)
cpu_load = CPULoadPlugin(check_interval=1.0)
memory_usage = MemoryUsagePlugin(check_interval=5.0)

# Flag to prevent re-entrant signal handler calls (use dict to avoid global statement)
_cleanup_state = {"in_progress": False}


def cleanup_display(sig=None, frame=None):
    """Clear the display when script is interrupted"""
    # Prevent re-entrant calls if cleanup is already in progress
    if _cleanup_state["in_progress"]:
        logger.warning("Force exit...")
        sys.exit(1)

    _cleanup_state["in_progress"] = True
    logger.info("Cleaning up display...")

    try:
        # Clear display by drawing all black
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        disp.image(image)
        disp.show()
        logger.info("Display cleared. Exiting.")
    except Exception as e:
        # If display cleanup fails, still exit gracefully
        logger.error(f"Error clearing display during cleanup: {e}")
        logger.info("Exiting anyway.")
    finally:
        sys.exit(0)


# Register signal handlers for clean shutdown
signal.signal(signal.SIGINT, cleanup_display)  # CTRL+C
signal.signal(signal.SIGTERM, cleanup_display)  # Termination signal

logger.info("Starting sensor monitoring with hot-pluggable support...")
logger.info("Sensors will be automatically detected when connected.")
logger.info("Press CTRL+C to stop and clear the display.")
print()  # Blank line for readability

# Performance tracking
frame_times = []
max_frame_times = 100  # Keep last 100 frame times for FPS calculation
last_frame_time = None  # Initialize to None to skip first frame timing

# Performance tracking
frame_times = []
max_frame_times = 100  # Keep last 100 frame times for FPS calculation
last_frame_time = None  # Initialize to None to skip first frame timing

try:
    previous_display_state = True
    while True:
        frame_start = time.time()

        # Check if display should be active
        display_should_be_active = timeout_manager.should_display_be_active()

        if display_should_be_active:
            # Draw a black filled box to clear the image.
            draw.rectangle((0, 0, width, height), outline=0, fill=0)

            # Read sensor data using plugins
            temp_data = tmp117.read()
            light_data = veml7700.read()
            bme_data = bme680.read()
            ip_data = ip_address.read()
            cpu_data = cpu_load.read()
            memory_data = memory_usage.read()

            # Use plugin format methods
            temp_str = tmp117.format_display(temp_data)
            light_str = veml7700.format_display(light_data)
            air_quality_str = bme680.format_display(bme_data)

            # Get system info from plugins
            ip = ip_data.get("ip_address", "n/a")
            cpu = cpu_data.get("cpu_load", "n/a")
            memory = memory_data.get("memory_usage", "n/a")

            # Calculate FPS
            current_time = time.time()
            if last_frame_time is not None:
                frame_time = current_time - last_frame_time
                frame_times.append(frame_time)
                if len(frame_times) > max_frame_times:
                    frame_times.pop(0)

            fps = 0
            if len(frame_times) > 0:
                avg_frame_time = sum(frame_times) / len(frame_times)
                fps = 1.0 / avg_frame_time

            # Write four lines of text on the display.
            draw.text((x, top + 0), f"IP: {ip} FPS:{fps:.0f}", font=font, fill=255)
            draw.text((x, top + 8), f"{temp_str} CPU: {cpu} {light_str}", font=font, fill=255)
            draw.text((x, top + 16), f"Mem: {memory}", font=font, fill=255)
            draw.text((x, top + 25), air_quality_str, font=font, fill=255)

            # Display image.
            disp.image(image)
            disp.show()

            # Track frame timing
            frame_end = time.time()
            display_time = frame_end - frame_start
            last_frame_time = current_time

            # Log performance every 10 frames
            if len(frame_times) > 0 and len(frame_times) % 10 == 0:
                logger.info(f"Display update: {display_time * 1000:.1f}ms | FPS: {fps:.1f}")
        # Display is timed out - blank it once when state changes
        elif previous_display_state:
            logger.info("Display blanked due to inactivity")
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            disp.image(image)
            disp.show()

        previous_display_state = display_should_be_active
        time.sleep(0.1)
except KeyboardInterrupt:
    # This is a backup in case signal handler doesn't trigger
    cleanup_display()
except Exception as e:
    logger.error(f"Error occurred: {e}")
    cleanup_display()
