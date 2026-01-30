# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Web server to visualize SSD1305 display output with mocked sensors
"""

import io
import random
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Mock sensor classes for testing without hardware


class MockTMP117:
    """Mock TMP117 temperature sensor"""

    def __init__(self):
        self.base_temp = 22.0

    def begin(self):
        return True

    def read_temp_c(self):
        # Simulate temperature variation
        return self.base_temp + random.uniform(-2.0, 2.0)


class MockVEML7700:
    """Mock VEML7700 light sensor"""

    def __init__(self, i2c):
        self.base_light = 100

    @property
    def light(self):
        # Simulate light variation
        return self.base_light + random.uniform(-20, 20)


class MockBME680Data:
    """Mock BME680 sensor data"""

    def __init__(self):
        self.temperature = 23.0 + random.uniform(-1, 1)
        self.humidity = 45.0 + random.uniform(-5, 5)
        self.pressure = 1013.25 + random.uniform(-10, 10)
        self.gas_resistance = 50000 + random.uniform(-5000, 5000)
        self.heat_stable = True


class MockBME680:
    """Mock BME680 environmental sensor"""

    I2C_ADDR_SECONDARY = 0x77
    OS_2X = 2
    OS_4X = 4
    OS_8X = 8
    FILTER_SIZE_3 = 3
    ENABLE_GAS_MEAS = 1

    def __init__(self, addr):
        self.data = MockBME680Data()

    def set_humidity_oversample(self, value):
        pass

    def set_pressure_oversample(self, value):
        pass

    def set_temperature_oversample(self, value):
        pass

    def set_filter(self, value):
        pass

    def set_gas_status(self, value):
        pass

    def set_gas_heater_temperature(self, value):
        pass

    def set_gas_heater_duration(self, value):
        pass

    def select_gas_heater_profile(self, value):
        pass

    def get_sensor_data(self):
        self.data = MockBME680Data()
        return True


# Replace actual sensor imports with mocks
sys.modules["qwiic_tmp117"] = type(sys)("qwiic_tmp117")
sys.modules["qwiic_tmp117"].QwiicTMP117 = MockTMP117
sys.modules["adafruit_veml7700"] = type(sys)("adafruit_veml7700")
sys.modules["adafruit_veml7700"].VEML7700 = MockVEML7700
sys.modules["bme680"] = type(sys)("bme680")
for attr in dir(MockBME680):
    if not attr.startswith("_"):
        setattr(sys.modules["bme680"], attr, getattr(MockBME680, attr))

# Add parent directory to path to import sensor_plugin
sys.path.insert(0, str(Path(__file__).parent.parent))
from sensor_plugin import BME680Plugin, TMP117Plugin, VEML7700Plugin


class DisplaySimulator:
    """Simulate the SSD1305 display"""

    def __init__(self, width=128, height=32):
        self.width = width
        self.height = height
        self.image = Image.new("1", (width, height))
        self.draw = ImageDraw.Draw(self.image)

    def clear(self):
        """Clear the display"""
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

    def get_image_bytes(self):
        """Get display as PNG bytes"""
        # Convert 1-bit image to RGB for better visibility
        rgb_image = Image.new("RGB", (self.width, self.height))
        for y in range(self.height):
            for x in range(self.width):
                pixel = self.image.getpixel((x, y))
                # White on black background
                rgb_image.putpixel((x, y), (255, 255, 255) if pixel else (0, 0, 0))

        # Scale up for better visibility
        scale = 4
        rgb_image = rgb_image.resize(
            (self.width * scale, self.height * scale), Image.NEAREST
        )

        buffer = io.BytesIO()
        rgb_image.save(buffer, format="PNG")
        return buffer.getvalue()


class DisplayServer(BaseHTTPRequestHandler):
    """HTTP server to display the simulated OLED"""

    display = None
    tmp117 = None
    veml7700 = None
    bme680 = None
    font = None
    last_update = 0

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.get_html().encode())
        elif self.path == "/display.png":
            self.update_display()
            self.send_response(200)
            self.send_header("Content-type", "image/png")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(self.display.get_image_bytes())
        else:
            self.send_response(404)
            self.end_headers()

    def update_display(self):
        """Update the display with current sensor readings"""
        current_time = time.time()
        if current_time - self.last_update < 0.1:
            return

        self.last_update = current_time

        # Clear display
        self.display.clear()

        # Read sensor data
        temp_data = self.tmp117.read()
        light_data = self.veml7700.read()
        bme_data = self.bme680.read()

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

        # Get system info
        # Note: shell=True is used here with static strings (no user input) for convenience
        try:
            cmd = "hostname -I | cut -d' ' -f1"
            IP = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            if not IP:
                IP = "127.0.0.1"
        except Exception:
            IP = "127.0.0.1"

        try:
            cmd = "top -bn1 | grep load | awk '{printf \"CPU: %.2f\", $(NF-2)}'"
            CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except Exception:
            CPU = "CPU: 0.50"

        try:
            cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB\", $3,$2}'"
            MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except Exception:
            MemUsage = "Mem: 512/2048 MB"

        # Draw text on display
        padding = -2
        top = padding
        x = 0

        self.display.draw.text((x, top + 0), f"IP: {IP}", font=self.font, fill=255)
        self.display.draw.text(
            (x, top + 8), f"{temp_str} {CPU} {light_str}", font=self.font, fill=255
        )
        self.display.draw.text((x, top + 16), MemUsage, font=self.font, fill=255)

        # Display air quality score or burn-in status
        air_quality = bme_data.get("air_quality", "n/a")
        burn_in_remaining = bme_data.get("burn_in_remaining")

        if burn_in_remaining is not None:
            self.display.draw.text(
                (x, top + 25), f"Burn-in: {burn_in_remaining}s", font=self.font, fill=255
            )
        elif air_quality != "n/a":
            self.display.draw.text(
                (x, top + 25), f"AirQ: {air_quality:.1f}", font=self.font, fill=255
            )
        else:
            self.display.draw.text((x, top + 25), "AirQ: n/a", font=self.font, fill=255)

    def get_html(self):
        """Return the HTML page"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>SSD1305 Display Simulator</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f0f0f0;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .display-container {
            text-align: center;
            margin: 20px 0;
            padding: 20px;
            background-color: #000;
            border-radius: 5px;
        }
        #display {
            border: 2px solid #333;
            image-rendering: pixelated;
            image-rendering: -moz-crisp-edges;
            image-rendering: crisp-edges;
        }
        .info {
            margin-top: 20px;
            padding: 15px;
            background-color: #e8f4f8;
            border-radius: 5px;
        }
        .info h2 {
            margin-top: 0;
            color: #2c5aa0;
        }
        .info ul {
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>SSD1305 Display Simulator</h1>
        <div class="display-container">
            <img id="display" src="/display.png" alt="OLED Display">
        </div>
        <div class="info">
            <h2>About This Demo</h2>
            <ul>
                <li><strong>Hot-pluggable sensors:</strong> Sensors are automatically detected and show "n/a" when not available</li>
                <li><strong>Plugin system:</strong> Each sensor is a modular plugin that handles its own initialization and error handling</li>
                <li><strong>Mocked hardware:</strong> This demo uses simulated sensors for testing without physical hardware</li>
                <li><strong>Auto-refresh:</strong> Display updates automatically every 200ms</li>
            </ul>
        </div>
    </div>
    <script>
        // Auto-refresh the display image
        function refreshDisplay() {
            var img = document.getElementById('display');
            img.src = '/display.png?' + new Date().getTime();
        }
        setInterval(refreshDisplay, 200);
    </script>
</body>
</html>
"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_server(port=8000):
    """Run the display server"""
    # Initialize display simulator
    DisplayServer.display = DisplaySimulator(128, 32)

    # Load font
    try:
        DisplayServer.font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9
        )
    except Exception:
        DisplayServer.font = ImageFont.load_default()

    # Initialize sensor plugins
    DisplayServer.tmp117 = TMP117Plugin(check_interval=5.0)
    DisplayServer.veml7700 = VEML7700Plugin(check_interval=5.0)
    DisplayServer.bme680 = BME680Plugin(check_interval=5.0, burn_in_time=30)

    # Start server
    server_address = ("", port)
    httpd = HTTPServer(server_address, DisplayServer)
    print(f"Server running on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
