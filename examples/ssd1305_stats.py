# SPDX-FileCopyrightText: <text> 2020 Tony DiCola, James DeVito,
# and 2020 Melissa LeBlanc-Williams, for Adafruit Industries </text>

# SPDX-License-Identifier: MIT


# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import subprocess
import time

import adafruit_veml7700
import board
import busio
import digitalio
import qwiic_tmp117
from board import D4, SCL, SDA
from PIL import Image, ImageDraw, ImageFont

import adafruit_ssd1305

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
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)

myTMP117 = qwiic_tmp117.QwiicTMP117()
myTMP117.begin()

tempC = myTMP117.read_temp_c()

i2c = board.I2C()  # uses board.SCL and board.SDA
veml7700 = adafruit_veml7700.VEML7700(i2c)



import bme680

bme680sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

bme680sensor.set_humidity_oversample(bme680.OS_2X)
bme680sensor.set_pressure_oversample(bme680.OS_4X)
bme680sensor.set_temperature_oversample(bme680.OS_8X)
bme680sensor.set_filter(bme680.FILTER_SIZE_3)

bme680sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
bme680sensor.set_gas_heater_temperature(320)
bme680sensor.set_gas_heater_duration(150)
bme680sensor.select_gas_heater_profile(0)

# from https://github.com/pimoroni/bme680-python/blob/main/examples/indoor-air-quality.py


# start_time and curr_time ensure that the
# burn_in_time (in seconds) is kept track of.

start_time = time.time()
curr_time = time.time()
burn_in_time = 300

burn_in_data = []

# Collect gas resistance burn-in values, then use the average
# of the last 50 values to set the upper limit for calculating
# gas_baseline.
print('Collecting gas resistance burn-in data for 5 mins\n')
while curr_time - start_time < burn_in_time:
    curr_time = time.time()
    if bme680sensor.get_sensor_data() and bme680sensor.data.heat_stable:
        gas = bme680sensor.data.gas_resistance
        burn_in_data.append(gas)
        print(f'Gas: {gas} Ohms')
        time.sleep(1)

gas_baseline = sum(burn_in_data[-50:]) / 50.0

# Set the humidity baseline to 40%, an optimal indoor humidity.
hum_baseline = 40.0

# This sets the balance between humidity and gas reading in the
# calculation of air_quality_score (25:75, humidity:gas)
hum_weighting = 0.25

print(f'Gas baseline: {gas_baseline} Ohms, humidity baseline: {hum_baseline:.2f} %RH\n')

while True:
    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    tempC = "T:" + format(myTMP117.read_temp_c(), ".2f") + " "
    print("Ambient light:", veml7700.light)

    if bme680sensor.get_sensor_data() and bme680sensor.data.heat_stable:
        gas = bme680sensor.data.gas_resistance
        gas_offset = gas_baseline - gas

        hum = bme680sensor.data.humidity
        hum_offset = hum - hum_baseline

        # Calculate hum_score as the distance from the hum_baseline.
        if hum_offset > 0:
            hum_score = (100 - hum_baseline - hum_offset)
            hum_score /= (100 - hum_baseline)
            hum_score *= (hum_weighting * 100)

        else:
            hum_score = (hum_baseline + hum_offset)
            hum_score /= hum_baseline
            hum_score *= (hum_weighting * 100)

        # Calculate gas_score as the distance from the gas_baseline.
        if gas_offset > 0:
            gas_score = (gas / gas_baseline)
            gas_score *= (100 - (hum_weighting * 100))

        else:
            gas_score = 100 - (hum_weighting * 100)

        # Calculate air_quality_score.
        air_quality_score = hum_score + gas_score

        print(f'Gas: {gas:.2f} Ohms, humidity: {hum:.2f} %RH, air quality: {air_quality_score:.2f}')

    # Shell scripts for system monitoring from here:
    # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname -I | cut -d' ' -f1"
    IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "top -bn1 | grep load | awk '{printf \"CPU: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\''
    Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")

    # Write four lines of text.

    draw.text((x, top + 0), "IP: " + IP, font=font, fill=255)
    draw.text((x, top + 8), tempC + CPU + " light:" + str(veml7700.light), font=font, fill=255)
    draw.text((x, top + 16), MemUsage, font=font, fill=255)
    draw.text((x, top + 25), Disk, font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(0.1)
