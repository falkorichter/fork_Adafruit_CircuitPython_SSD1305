# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Web server to visualize SSD1305 display output with mocked sensors
"""

import io
import random
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
    ip_address = None
    cpu_load = None
    memory_usage = None
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
        ip_data = self.ip_address.read()
        cpu_data = self.cpu_load.read()
        memory_data = self.memory_usage.read()

        # Use plugin format methods
        temp_str = self.tmp117.format_display(temp_data)
        light_str = self.veml7700.format_display(light_data)
        air_quality_str = self.bme680.format_display(bme_data)

        # Get system info
        ip = ip_data.get("ip_address", "n/a")
        cpu = cpu_data.get("cpu_load", "n/a")
        memory = memory_data.get("memory_usage", "n/a")

        # Draw text on display
        padding = -2
        top = padding
        x = 0

        self.display.draw.text((x, top + 0), f"IP: {ip}", font=self.font, fill=255)
        self.display.draw.text(
            (x, top + 8), f"{temp_str} CPU: {cpu} {light_str}", font=self.font, fill=255
        )
        self.display.draw.text((x, top + 16), f"Mem: {memory}", font=self.font, fill=255)
        self.display.draw.text((x, top + 25), air_quality_str, font=self.font, fill=255)

    def get_html(self):
        """Return the HTML page"""
        # Load HTML template from file
        template_path = Path(__file__).parent / "web_simulator_template.html"
        try:
            with open(template_path) as f:
                return f.read()
        except FileNotFoundError:
            # Fallback to inline HTML if template not found
            return """
<!DOCTYPE html>
<html>
<head>
    <title>SSD1305 Display Simulator</title>
</head>
<body>
    <h1>SSD1305 Display Simulator</h1>
    <img id="display" src="/display.png" alt="OLED Display">
    <script>
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
    DisplayServer.ip_address = IPAddressPlugin(check_interval=30.0)
    DisplayServer.cpu_load = CPULoadPlugin(check_interval=1.0)
    DisplayServer.memory_usage = MemoryUsagePlugin(check_interval=5.0)

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
