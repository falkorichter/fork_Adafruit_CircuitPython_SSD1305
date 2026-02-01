"""
Web server to visualize SSD1305 display output with optional mocked sensors
"""

import asyncio
import base64
import io
import json
import random
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw, ImageFont

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

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
        # Send small image and let browser scale it with CSS for much better performance
        # On Raspberry Pi: ~6-10ms vs ~120ms with server-side scaling
        rgb_image = self.image.convert("RGB")

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
    
    # Detailed benchmarking
    sensor_read_times = []
    display_render_times = []
    png_generation_times = []
    
    # Cached sensor data for non-blocking reads
    cached_sensor_data = None
    sensor_data_lock = threading.Lock()
    
    # WebSocket clients
    websocket_clients = set()
    websocket_lock = threading.Lock()

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
        elif path == "/benchmark":
            # Serve static benchmark page
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.get_benchmark_html().encode())
        elif path == "/display.png":
            start_time = time.time()
            png_bytes = self.get_cached_display_image()
            
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
            stats = self.get_performance_stats()
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _read_fresh_sensor_data(self):
        """Read fresh sensor data from all sensors"""
        sensor_start = time.time()
        temp_data = self.tmp117.read()
        light_data = self.veml7700.read()
        bme_data = self.bme680.read()
        ip_data = self.ip_address.read()
        cpu_data = self.cpu_load.read()
        memory_data = self.memory_usage.read()
        sensor_time = time.time() - sensor_start
        
        DisplayServer.sensor_read_times.append(sensor_time)
        if len(DisplayServer.sensor_read_times) > 100:
            DisplayServer.sensor_read_times.pop(0)
        
        return {
            'temp': temp_data,
            'light': light_data,
            'bme': bme_data,
            'ip': ip_data,
            'cpu': cpu_data,
            'memory': memory_data
        }
    
    def update_display(self):
        """Update the display with current sensor readings"""
        # Clear display
        self.display.clear()

        # Use cached sensor data if available
        with DisplayServer.sensor_data_lock:
            if DisplayServer.cached_sensor_data is None:
                # First time or cache expired, read fresh data
                DisplayServer.cached_sensor_data = self._read_fresh_sensor_data()
            
            sensor_data = DisplayServer.cached_sensor_data

        # Time display rendering separately
        render_start = time.time()
        
        # Use plugin format methods
        temp_str = self.tmp117.format_display(sensor_data['temp'])
        light_str = self.veml7700.format_display(sensor_data['light'])
        air_quality_str = self.bme680.format_display(sensor_data['bme'])

        # Get system info
        ip = sensor_data['ip'].get("ip_address", "n/a")
        cpu = sensor_data['cpu'].get("cpu_load", "n/a")
        memory = sensor_data['memory'].get("memory_usage", "n/a")

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
        
        render_time = time.time() - render_start
        DisplayServer.display_render_times.append(render_time)
        if len(DisplayServer.display_render_times) > 100:
            DisplayServer.display_render_times.pop(0)
    
    def get_cached_display_image(self):
        """Get the display image, using update_display to refresh it"""
        png_start = time.time()
        self.update_display()
        png_bytes = self.display.get_image_bytes()
        png_time = time.time() - png_start
        
        DisplayServer.png_generation_times.append(png_time)
        if len(DisplayServer.png_generation_times) > 100:
            DisplayServer.png_generation_times.pop(0)
        
        return png_bytes
    
    def get_performance_stats(self):
        """Get detailed performance statistics"""
        stats = {
            "fps": 0,
            "frame_count": len(DisplayServer.frame_times),
            "sensor_read_ms": 0,
            "display_render_ms": 0,
            "png_generation_ms": 0,
            "recommended_refresh_ms": 2000,
            "websockets_available": WEBSOCKETS_AVAILABLE
        }
        
        if len(DisplayServer.frame_times) > 0:
            avg_frame_time = sum(DisplayServer.frame_times) / len(DisplayServer.frame_times)
            stats["fps"] = round(1.0 / avg_frame_time, 1)
            # Recommend refresh rate slightly faster than actual FPS (90% of frame time)
            # This ensures the client polls slightly faster than content updates to minimize lag
            stats["recommended_refresh_ms"] = max(100, int(avg_frame_time * 0.9 * 1000))
        
        if len(DisplayServer.sensor_read_times) > 0:
            avg_sensor = (
                sum(DisplayServer.sensor_read_times)
                / len(DisplayServer.sensor_read_times)
                * 1000
            )
            stats["sensor_read_ms"] = round(avg_sensor, 1)
        
        if len(DisplayServer.display_render_times) > 0:
            avg_render = (
                sum(DisplayServer.display_render_times)
                / len(DisplayServer.display_render_times)
                * 1000
            )
            stats["display_render_ms"] = round(avg_render, 1)
        
        if len(DisplayServer.png_generation_times) > 0:
            avg_png = (
                sum(DisplayServer.png_generation_times)
                / len(DisplayServer.png_generation_times)
                * 1000
            )
            stats["png_generation_ms"] = round(avg_png, 1)
        
        return stats

    def get_html(self):
        """Return the HTML page"""
        # Load HTML template from file
        template_path = Path(__file__).parent / "web_simulator_template.html"
        with open(template_path) as f:
            html = f.read()
        
        # Inject the use_mocks value and update mode text
        mode_text = "mocked sensors" if self.use_mocks else "real sensors"
        use_mocks_str = str(self.use_mocks).lower()
        html = html.replace('const useMocks = false;', f'const useMocks = {use_mocks_str};')
        html = html.replace(
            '<span id="mode-text">real sensors</span>',
            f'<span id="mode-text">{mode_text}</span>'
        )
        ws_available_str = str(WEBSOCKETS_AVAILABLE).lower()
        html = html.replace(
            'const WEBSOCKETS_AVAILABLE = false;',
            f'const WEBSOCKETS_AVAILABLE = {ws_available_str};'
        )
        
        return html
    
    def get_benchmark_html(self):
        """Return a static benchmark HTML page for measuring base server performance"""
        # ruff: noqa: E501
        return '''<!DOCTYPE html>
<html>
<head>
    <title>Static Benchmark - SSD1305 Display Simulator</title>
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
        .benchmark-results {
            margin: 20px 0;
            padding: 20px;
            background-color: #e8f4f8;
            border-radius: 5px;
        }
        .metric {
            padding: 10px;
            margin: 5px 0;
            background-color: white;
            border-left: 3px solid #2c5aa0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Static Benchmark Page</h1>
        <div class="benchmark-results">
            <h2>Benchmark Results</h2>
            <div id="results">
                <div class="metric">
                    <strong>Total Requests:</strong> <span id="total-requests">0</span>
                </div>
                <div class="metric">
                    <strong>Average Response Time:</strong> <span id="avg-response">--</span> ms
                </div>
                <div class="metric">
                    <strong>Min Response Time:</strong> <span id="min-response">--</span> ms
                </div>
                <div class="metric">
                    <strong>Max Response Time:</strong> <span id="max-response">--</span> ms
                </div>
                <div class="metric">
                    <strong>Requests per Second:</strong> <span id="rps">--</span>
                </div>
            </div>
        </div>
        <div style="margin-top: 20px; padding: 15px; background-color: #f9f9f9; border-left: 3px solid #4CAF50;">
            <strong>Purpose:</strong> This static page benchmarks the base server performance without
            any dynamic content generation. Compare this with the dynamic display page to understand
            the overhead of PNG generation and sensor reading.
        </div>
    </div>
    <script>
        let requestCount = 0;
        let responseTimes = [];
        let startTime = Date.now();
        
        function updateBenchmark() {
            const reqStart = performance.now();
            fetch('/benchmark')
                .then(response => {
                    const reqEnd = performance.now();
                    const responseTime = reqEnd - reqStart;
                    requestCount++;
                    responseTimes.push(responseTime);
                    
                    // Keep only last 100 measurements
                    if (responseTimes.length > 100) {
                        responseTimes.shift();
                    }
                    
                    // Update UI
                    document.getElementById('total-requests').textContent = requestCount;
                    
                    if (responseTimes.length > 0) {
                        const avg = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
                        const min = Math.min(...responseTimes);
                        const max = Math.max(...responseTimes);
                        
                        document.getElementById('avg-response').textContent = avg.toFixed(1);
                        document.getElementById('min-response').textContent = min.toFixed(1);
                        document.getElementById('max-response').textContent = max.toFixed(1);
                        
                        const elapsed = (Date.now() - startTime) / 1000;
                        const rps = requestCount / elapsed;
                        document.getElementById('rps').textContent = rps.toFixed(1);
                    }
                })
                .catch(error => console.error('Error:', error));
        }
        
        // Run benchmark continuously
        setInterval(updateBenchmark, 100);
    </script>
</body>
</html>'''

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_server(port=8000, use_mocks=False, enable_websocket=False, websocket_port=8001):
    """Run the display server
    
    Args:
        port: Port to run server on
        use_mocks: If True, use mocked sensors. If False, use real sensors.
        enable_websocket: If True, enable WebSocket server for push updates
        websocket_port: Port for WebSocket server
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
    DisplayServer.sensor_read_times = []
    DisplayServer.display_render_times = []
    DisplayServer.png_generation_times = []
    DisplayServer.cached_sensor_data = None
    
    # Start background thread for sensor data collection
    def update_sensor_cache():
        """Background thread to update sensor cache"""
        while True:
            time.sleep(0.5)  # Update sensors every 500ms
            # Directly update the cache instead of just invalidating it
            try:
                # Create a temporary handler instance to access sensor reading method
                handler = DisplayServer(None, None, None)
                with DisplayServer.sensor_data_lock:
                    DisplayServer.cached_sensor_data = handler._read_fresh_sensor_data()
            except Exception:
                # If update fails, invalidate cache to force refresh on next display update
                with DisplayServer.sensor_data_lock:
                    DisplayServer.cached_sensor_data = None
    
    sensor_thread = threading.Thread(target=update_sensor_cache, daemon=True)
    sensor_thread.start()
    print("Started background sensor update thread")

    # Start WebSocket server if enabled and available
    if enable_websocket and WEBSOCKETS_AVAILABLE:
        async def websocket_handler(websocket):
            """Handle WebSocket connections"""
            with DisplayServer.websocket_lock:
                DisplayServer.websocket_clients.add(websocket)
            num_clients = len(DisplayServer.websocket_clients)
            print(f"WebSocket client connected. Total clients: {num_clients}")

            try:
                # Send initial image
                png_bytes = DisplayServer.display.get_image_bytes()
                await websocket.send(json.dumps({
                    'type': 'image',
                    'data': base64.b64encode(png_bytes).decode('utf-8')
                }))

                # Keep connection alive and send updates
                while True:
                    await asyncio.sleep(0.5)  # Send updates every 500ms
                    png_bytes = DisplayServer.display.get_image_bytes()
                    await websocket.send(json.dumps({
                        'type': 'image',
                        'data': base64.b64encode(png_bytes).decode('utf-8')
                    }))
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                with DisplayServer.websocket_lock:
                    DisplayServer.websocket_clients.discard(websocket)
                num_clients = len(DisplayServer.websocket_clients)
                print(f"WebSocket client disconnected. Total clients: {num_clients}")
        
        def run_websocket_server():
            """Run WebSocket server in event loop"""
            async def start_websocket():
                async with websockets.serve(websocket_handler, "0.0.0.0", websocket_port):
                    await asyncio.Future()  # run forever
            
            asyncio.run(start_websocket())
        
        ws_thread = threading.Thread(target=run_websocket_server, daemon=True)
        ws_thread.start()
        print(f"WebSocket server running on ws://localhost:{websocket_port}")
    elif enable_websocket and not WEBSOCKETS_AVAILABLE:
        print("WebSocket support requested but 'websockets' module not installed")
        print("Install with: pip install websockets")

    # Start server
    server_address = ("", port)
    httpd = HTTPServer(server_address, DisplayServer)
    print(f"HTTP server running on http://localhost:{port}")
    print(f"Benchmark page: http://localhost:{port}/benchmark")
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
    parser.add_argument(
        '--port', type=int, default=8000,
        help='Port to run HTTP server on (default: 8000)'
    )
    parser.add_argument(
        '--use-mocks', action='store_true',
        help='Use mocked sensors instead of real hardware'
    )
    parser.add_argument(
        '--enable-websocket', action='store_true',
        help='Enable WebSocket server for push updates'
    )
    parser.add_argument(
        '--websocket-port', type=int, default=8001,
        help='Port to run WebSocket server on (default: 8001)'
    )
    args = parser.parse_args()

    run_server(port=args.port, use_mocks=args.use_mocks,
               enable_websocket=args.enable_websocket,
               websocket_port=args.websocket_port)
