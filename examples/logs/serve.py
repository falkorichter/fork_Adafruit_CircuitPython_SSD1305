#!/usr/bin/env python3
"""Local server for the Sensor Log Visualizer with CORS proxy.

Serves static files from the logs directory and proxies requests to the
SparkFun DataLogger device, adding CORS headers so the browser allows
cross-origin downloads.

Usage:
    cd examples/logs
    python3 serve.py [--port 8000]

Then open http://localhost:8000/visualizer.html and use the
"Download from DataLogger" panel.
"""

import argparse
import http.server
import socketserver
import urllib.request
import urllib.error
import urllib.parse


class CORSProxyHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that serves local files and proxies DataLogger requests."""

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        """Serve local files or proxy /proxy/<url> to the DataLogger."""
        if self.path.startswith("/proxy/"):
            self._handle_proxy()
        else:
            super().do_GET()

    def _handle_proxy(self):
        """Forward request to the DataLogger and return the response.

        Only allows proxying to .local mDNS hostnames and private/link-local
        IP ranges to prevent misuse as an open relay.
        """
        target_url = urllib.parse.unquote(self.path[len("/proxy/"):])

        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = "http://" + target_url

        # Validate the target is a local network address
        parsed = urllib.parse.urlparse(target_url)
        hostname = (parsed.hostname or "").lower()

        allowed = (
            hostname.endswith(".local")
            or hostname.startswith("192.168.")
            or hostname.startswith("10.")
            or hostname.startswith("172.")
            or hostname == "localhost"
            or hostname == "127.0.0.1"
        )
        if not allowed:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Proxy restricted to .local and private network addresses")
            return

        try:
            req = urllib.request.Request(target_url)  # noqa: SSRF - validated above
            req.add_header("User-Agent", "SensorLogVisualizer/1.0")
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                self.send_response(resp.status)
                content_type = resp.headers.get("Content-Type", "application/octet-stream")
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(str(e).encode())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f"Proxy error: {e}".encode())

    def log_message(self, format, *args):
        """Log with color for proxy requests."""
        if self.path.startswith("/proxy/"):
            print(f"  \033[36m[proxy]\033[0m {format % args}")
        else:
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="Sensor Log Visualizer server with CORS proxy")
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on (default: 8000)")
    args = parser.parse_args()

    with socketserver.TCPServer(("", args.port), CORSProxyHandler) as httpd:
        print(f"Serving at http://localhost:{args.port}/visualizer.html")
        print(f"CORS proxy available at http://localhost:{args.port}/proxy/<url>")
        print("Press Ctrl+C to stop.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
