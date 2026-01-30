# SPDX-FileCopyrightText: <text> 2020 Tony DiCola, James DeVito,
# and 2020 Melissa LeBlanc-Williams, for Adafruit Industries </text>

# SPDX-License-Identifier: MIT


# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import subprocess
import sys
import time
from pathlib import Path

import board
import busio
import digitalio
from board import D4, SCL, SDA
from PIL import Image, ImageDraw, ImageFont

import adafruit_ssd1305

# Add parent directory to path to import sensor_plugin
sys.path.insert(0, str(Path(__file__).parent.parent))
from sensor_plugin import BME680Plugin, TMP117Plugin, VEML7700Plugin

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

print("Starting sensor monitoring with hot-pluggable support...")
print("Sensors will be automatically detected when connected.\n")

while True:
    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Read sensor data using plugins
    temp_data = tmp117.read()
    light_data = veml7700.read()
    bme_data = bme680.read()

    # Format temperature display
    temp_c = temp_data["temp_c"]
    if temp_c == "n/a":
        temp_str = "T:n/a"
    else:
        temp_str = f"T:{temp_c:.2f}"

    # Format light display
    light = light_data["light"]
    if light == "n/a":
        light_str = "light:n/a"
    else:
        light_str = f"light:{light:.0f}"

    # Shell scripts for system monitoring from here:
    # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    # Note: shell=True is used here with static strings (no user input) for convenience
    cmd = "hostname -I | cut -d' ' -f1"
    IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "top -bn1 | grep load | awk '{printf \"CPU: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")

    # Write four lines of text on the display.
    draw.text((x, top + 0), "IP: " + IP, font=font, fill=255)
    draw.text((x, top + 8), f"{temp_str} {CPU} {light_str}", font=font, fill=255)
    draw.text((x, top + 16), MemUsage, font=font, fill=255)

    # Display air quality score or burn-in status on the 4th line
    air_quality = bme_data.get("air_quality", "n/a")
    burn_in_remaining = bme_data.get("burn_in_remaining")

    if burn_in_remaining is not None:
        draw.text((x, top + 25), f"Burn-in: {burn_in_remaining}s", font=font, fill=255)
    elif air_quality != "n/a":
        draw.text((x, top + 25), f"AirQ: {air_quality:.1f}", font=font, fill=255)
    else:
        draw.text((x, top + 25), "AirQ: n/a", font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(0.1)
