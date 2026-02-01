# SPDX-FileCopyrightText: <text> 2020 Tony DiCola, James DeVito,
# and 2020 Melissa LeBlanc-Williams, for Adafruit Industries </text>

# SPDX-License-Identifier: MIT


# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import signal
import sys
import time
from pathlib import Path

import board
import busio
import digitalio
from board import D4, SCL, SDA
from PIL import Image, ImageDraw, ImageFont

import adafruit_ssd1305

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
        print("\nForce exit...")
        sys.exit(1)
    
    _cleanup_state["in_progress"] = True
    print("\nCleaning up display...")
    
    try:
        # Clear display by drawing all black
        draw.rectangle((0, 0, width, height), outline=0, fill=0)
        disp.image(image)
        disp.show()
        print("Display cleared. Exiting.")
    except Exception as e:
        # If display cleanup fails, still exit gracefully
        print(f"Error during cleanup: {e}")
        print("Exiting anyway.")
    finally:
        sys.exit(0)


# Register signal handlers for clean shutdown
signal.signal(signal.SIGINT, cleanup_display)  # CTRL+C
signal.signal(signal.SIGTERM, cleanup_display)  # Termination signal

print("Starting sensor monitoring with hot-pluggable support...")
print("Sensors will be automatically detected when connected.")
print("Press CTRL+C to stop and clear the display.\n")

# Performance tracking
frame_times = []
max_frame_times = 100  # Keep last 100 frame times for FPS calculation
last_frame_time = None  # Initialize to None to skip first frame timing

try:
    while True:
        frame_start = time.time()
        
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
            print(f"Display update: {display_time*1000:.1f}ms | FPS: {fps:.1f}")
        
        time.sleep(0.1)
except KeyboardInterrupt:
    # This is a backup in case signal handler doesn't trigger
    cleanup_display()
except Exception as e:
    print(f"\nError occurred: {e}")
    cleanup_display()
