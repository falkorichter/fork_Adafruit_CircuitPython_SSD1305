"""
Web server to visualize SSD1305 display output with optional mocked sensors
"""

import io
import json
import random
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


# Add parent directory to path to import sensor_plugins
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_mocks():
    """Setup mock sensor modules"""
    # Replace actual sensor imports with mocks
    sys.modules["qwiic_tmp117"] = type(sys)("qwiic_tmp117")
    sys.modules["qwiic_tmp117"].QwiicTMP117 = MockTMP117
    sys.modules["adafruit_veml7700"] = type(sys)("adafruit_veml7700")
    sys.modules["adafruit_veml7700"].VEML7700 = MockVEML7700
    sys.modules["bme680"] = type(sys)("bme680")
    for attr in dir(MockBME680):
        if not attr.startswith("_"):
            setattr(sys.modules["bme680"], attr, getattr(MockBME680, attr))


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
        # Use convert() instead of pixel-by-pixel operation for much better performance
        rgb_image = self.image.convert("RGB")

        # Scale up for better visibility
        scale = 4
        rgb_image = rgb_image.resize(
            (self.width * scale, self.height * scale), Image.NEAREST
        )

        buffer = io.BytesIO()
        rgb_image.save(buffer, format="PNG", optimize=False)
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
    use_mocks = False  # Default to real sensors
    
    # Performance tracking
    last_update_time = None
    frame_times = []
    max_frame_times = 100  # Keep last 100 frame times for FPS calculation

    def do_GET(self):
        """Handle GET requests"""
        # Parse the path and query parameters
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        if path == "/":
            # Check if use_mocks parameter is present
            use_mocks_param = query_params.get('use_mocks', ['false'])[0].lower()
            self.use_mocks = use_mocks_param == 'true'
            
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.get_html().encode())
        elif path == "/display.png":
            start_time = time.time()
            self.update_display()
            png_bytes = self.display.get_image_bytes()
            
            # Track performance (use class variables to persist across requests)
            generation_time = time.time() - start_time
            if DisplayServer.last_update_time is not None:
                frame_time = time.time() - DisplayServer.last_update_time
                DisplayServer.frame_times.append(frame_time)
                if len(DisplayServer.frame_times) > DisplayServer.max_frame_times:
                    DisplayServer.frame_times.pop(0)
            DisplayServer.last_update_time = time.time()
            
            # Log performance every 10 frames
            if len(DisplayServer.frame_times) > 0 and len(DisplayServer.frame_times) % 10 == 0:
                avg_fps = 1.0 / (sum(DisplayServer.frame_times) / len(DisplayServer.frame_times))
                print(f"PNG generation: {generation_time*1000:.1f}ms | Avg FPS: {avg_fps:.1f}")
            
            self.send_response(200)
            self.send_header("Content-type", "image/png")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(png_bytes)
        elif path == "/stats":
            # Return performance stats as JSON
            stats = {
                "fps": 0,
                "frame_count": len(DisplayServer.frame_times)
            }
            if len(DisplayServer.frame_times) > 0:
                avg_frame_time = sum(DisplayServer.frame_times) / len(DisplayServer.frame_times)
                stats["fps"] = round(1.0 / avg_frame_time, 1)
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def update_display(self):
        """Update the display with current sensor readings"""
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
        with open(template_path) as f:
            html = f.read()
        
        # Inject the use_mocks value and update mode text
        mode_text = "mocked sensors" if self.use_mocks else "real sensors"
        html = html.replace('const useMocks = false;', f'const useMocks = {str(self.use_mocks).lower()};')
        html = html.replace('<span id="mode-text">real sensors</span>', f'<span id="mode-text">{mode_text}</span>')
        
        return html

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_server(port=8000, use_mocks=False):
    """Run the display server
    
    Args:
        port: Port to run server on
        use_mocks: If True, use mocked sensors. If False, use real sensors.
    """
    # Setup mocks if requested
    if use_mocks:
        setup_mocks()
        print("Using mocked sensors")
    else:
        print("Using real sensors (will show 'n/a' if not connected)")
    
    # Initialize display simulator
    DisplayServer.display = DisplaySimulator(128, 32)
    DisplayServer.use_mocks = use_mocks

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
    
    # Initialize performance tracking
    DisplayServer.last_update_time = None
    DisplayServer.frame_times = []

    # Start server
    server_address = ("", port)
    httpd = HTTPServer(server_address, DisplayServer)
    print(f"Server running on http://localhost:{port}")
    print("Use ?use_mocks=true in the URL to enable mocked sensors")
    print("Press Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        httpd.server_close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='SSD1305 Web Simulator')
    parser.add_argument('--port', type=int, default=8000, help='Port to run server on (default: 8000)')
    parser.add_argument('--use-mocks', action='store_true', help='Use mocked sensors instead of real hardware')
    args = parser.parse_args()
    
    run_server(port=args.port, use_mocks=args.use_mocks)
