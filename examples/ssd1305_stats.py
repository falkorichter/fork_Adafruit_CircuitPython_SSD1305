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


def keyboard_listener(timeout_manager):
    """
    Background thread to monitor keyboard activity using pynput

    :param timeout_manager: DisplayTimeoutManager instance to update on activity
    """
    pynput_failed = False
    try:
        from pynput import keyboard  # noqa: PLC0415

        def on_press(key):
            """Called when any key is pressed"""
            was_inactive = timeout_manager.register_activity()
            if was_inactive:
                logger.info("Display reactivated by keyboard input")

        # Start listening to keyboard events
        logger.info("Starting pynput keyboard listener...")
        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        # Check if listener started successfully
        time.sleep(0.5)
        if not listener.running:
            pynput_failed = True
            logger.warning("pynput listener failed to start (may need X11/display server)")
            listener.stop()
        else:
            logger.info("pynput keyboard listener active")
            listener.join()

    except ImportError:
        logger.warning("pynput library not available.")
        logger.warning("Install with: pip install pynput")
        pynput_failed = True
    except Exception as e:
        logger.warning(f"pynput keyboard monitoring failed: {e}")
        pynput_failed = True

    # Fallback to stdin monitoring if pynput doesn't work
    if pynput_failed:
        logger.info("Falling back to stdin activity monitoring")
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
                        sys.stdin.read(1024)
                    except OSError:
                        pass
                    was_inactive = timeout_manager.register_activity()
                    if was_inactive:
                        logger.info("Display reactivated by keyboard input")
        except Exception as e:
            logger.error(f"Stdin monitoring also failed: {e}")
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
args = parser.parse_args()

# Initialize timeout manager
timeout_enabled = not args.no_blank and args.blank_timeout > 0
timeout_manager = DisplayTimeoutManager(timeout_seconds=args.blank_timeout, enabled=timeout_enabled)

# Start keyboard monitoring thread if timeout is enabled
if timeout_enabled:
    keyboard_thread = threading.Thread(
        target=keyboard_listener, args=(timeout_manager,), daemon=True
    )
    keyboard_thread.start()
    logger.info(f"Display blanking enabled: {args.blank_timeout}s timeout (any key to reactivate)")
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
