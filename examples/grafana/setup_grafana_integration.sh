#!/bin/bash
#
# Quick setup script for Grafana integration with MQTT sensor dashboard
# 
# This script installs and configures:
#   - InfluxDB 2.x
#   - Telegraf
#   - Basic configuration
#
# Prerequisites:
#   - Raspberry Pi running Raspberry Pi OS (or any Debian-based Linux)
#   - MQTT broker already installed and running
#   - Grafana already installed (https://grafana.com/tutorials/install-grafana-on-raspberry-pi/)
#
# Usage:
#   chmod +x setup_grafana_integration.sh
#   ./setup_grafana_integration.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on ARM architecture (Raspberry Pi)
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
    print_warn "This script is designed for Raspberry Pi. Detected architecture: $ARCH"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_info "Starting Grafana integration setup..."

# =============================================================================
# Step 1: Install InfluxDB 2.x
# =============================================================================

print_info "Installing InfluxDB 2.x..."

if command -v influxd &> /dev/null; then
    print_warn "InfluxDB is already installed. Skipping installation."
else
    # Determine correct package for architecture
    if [[ "$ARCH" == "aarch64" ]]; then
        INFLUX_PKG="influxdb2-2.7.4-arm64.deb"
    else
        INFLUX_PKG="influxdb2-2.7.4-armhf.deb"
    fi
    
    print_info "Downloading InfluxDB package: $INFLUX_PKG"
    print_info "This may take a few minutes depending on your internet connection..."
    
    # Download with progress bar (remove -q for visibility)
    if ! wget --show-progress --progress=bar:force "https://dl.influxdata.com/influxdb/releases/$INFLUX_PKG" -O /tmp/influxdb.deb 2>&1; then
        print_error "Failed to download InfluxDB package"
        print_error "Please check your internet connection and try again"
        exit 1
    fi
    
    print_info "Installing InfluxDB..."
    sudo dpkg -i /tmp/influxdb.deb || true
    sudo apt-get install -f -y  # Fix any dependency issues
    
    print_info "Enabling and starting InfluxDB service..."
    sudo systemctl enable influxdb
    sudo systemctl start influxdb
    
    # Wait for InfluxDB to start
    print_info "Waiting for InfluxDB to start..."
    sleep 5
    
    print_info "InfluxDB installed successfully!"
    print_info "Access InfluxDB UI at: http://localhost:8086"
    print_warn "IMPORTANT: Complete InfluxDB setup in web UI:"
    print_warn "  1. Open http://localhost:8086"
    print_warn "  2. Create initial user and organization 'sensors'"
    print_warn "  3. Create bucket 'sensor_data'"
    print_warn "  4. Generate API token and save it"
    echo ""
    read -p "Press Enter after completing InfluxDB setup..."
fi

# =============================================================================
# Step 2: Install Telegraf
# =============================================================================

print_info "Installing Telegraf..."

if command -v telegraf &> /dev/null; then
    print_warn "Telegraf is already installed. Skipping installation."
else
    # Determine correct package for architecture
    if [[ "$ARCH" == "aarch64" ]]; then
        TELEGRAF_PKG="telegraf_1.29.0-1_arm64.deb"
    else
        TELEGRAF_PKG="telegraf_1.29.0-1_armhf.deb"
    fi
    
    print_info "Downloading Telegraf package: $TELEGRAF_PKG"
    print_info "This may take a few minutes depending on your internet connection..."
    
    # Download with progress bar (remove -q for visibility)
    if ! wget --show-progress --progress=bar:force "https://dl.influxdata.com/telegraf/releases/$TELEGRAF_PKG" -O /tmp/telegraf.deb 2>&1; then
        print_error "Failed to download Telegraf package"
        print_error "Please check your internet connection and try again"
        exit 1
    fi
    
    print_info "Installing Telegraf..."
    sudo dpkg -i /tmp/telegraf.deb || true
    sudo apt-get install -f -y  # Fix any dependency issues
    
    print_info "Telegraf installed successfully!"
fi

# =============================================================================
# Step 3: Configure Telegraf
# =============================================================================

print_info "Configuring Telegraf..."

# Ask for InfluxDB token
echo ""
print_warn "Enter your InfluxDB API token (from step 1):"
read -r INFLUX_TOKEN

if [[ -z "$INFLUX_TOKEN" ]]; then
    print_error "InfluxDB token cannot be empty!"
    exit 1
fi

# Backup existing config if it exists
if [[ -f /etc/telegraf/telegraf.conf ]]; then
    print_info "Backing up existing Telegraf config..."
    sudo cp /etc/telegraf/telegraf.conf /etc/telegraf/telegraf.conf.backup.$(date +%Y%m%d_%H%M%S)
fi

# Copy our custom config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/telegraf.conf"

if [[ ! -f "$CONFIG_FILE" ]]; then
    print_error "telegraf.conf not found at: $CONFIG_FILE"
    print_error "Make sure you run this script from the examples/grafana directory"
    exit 1
fi

print_info "Installing Telegraf configuration..."
sudo cp "$CONFIG_FILE" /etc/telegraf/telegraf.conf

# Replace token placeholder
sudo sed -i "s/\$INFLUX_TOKEN/$INFLUX_TOKEN/g" /etc/telegraf/telegraf.conf

print_info "Telegraf configuration installed!"

# =============================================================================
# Step 4: Test Configuration
# =============================================================================

print_info "Testing Telegraf configuration..."

if sudo telegraf --test --config /etc/telegraf/telegraf.conf 2>&1 | grep -q "Error"; then
    print_error "Telegraf configuration test failed!"
    print_error "Check the output above for errors"
    exit 1
else
    print_info "Telegraf configuration is valid!"
fi

# =============================================================================
# Step 5: Start Services
# =============================================================================

print_info "Starting Telegraf service..."
sudo systemctl enable telegraf
sudo systemctl restart telegraf

# Wait a moment for startup
sleep 2

# Check status
if sudo systemctl is-active --quiet telegraf; then
    print_info "Telegraf is running!"
else
    print_error "Telegraf failed to start. Check logs with: sudo journalctl -u telegraf -f"
    exit 1
fi

# =============================================================================
# Step 6: Verify Data Flow
# =============================================================================

print_info "Verifying data flow..."

print_info "Checking MQTT broker connectivity..."
if timeout 5 mosquitto_sub -h localhost -t iot_logger -C 1 &> /dev/null; then
    print_info "MQTT broker is accessible and publishing data!"
else
    print_warn "No MQTT messages received. Ensure your IoT device is publishing to 'iot_logger' topic"
fi

print_info "Checking InfluxDB connectivity..."
if curl -s http://localhost:8086/health | grep -q "pass"; then
    print_info "InfluxDB is healthy!"
else
    print_warn "InfluxDB health check failed"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo "=============================================================================="
print_info "Setup complete! 🎉"
echo "=============================================================================="
echo ""
echo "Next steps:"
echo "  1. Wait 1-2 minutes for data to accumulate in InfluxDB"
echo "  2. Open Grafana: http://localhost:3000"
echo "  3. Add InfluxDB datasource:"
echo "       - Settings → Data Sources → Add InfluxDB"
echo "       - Query Language: Flux"
echo "       - URL: http://localhost:8086"
echo "       - Organization: sensors"
echo "       - Token: (your InfluxDB token)"
echo "       - Default Bucket: sensor_data"
echo "  4. Import dashboard from examples/grafana/dashboard.json"
echo ""
echo "Useful commands:"
echo "  - View Telegraf logs:  sudo journalctl -u telegraf -f"
echo "  - View InfluxDB logs:  sudo journalctl -u influxdb -f"
echo "  - Restart Telegraf:    sudo systemctl restart telegraf"
echo "  - Check data in InfluxDB: influx query 'from(bucket:\"sensor_data\") |> range(start: -1h) |> limit(n:10)'"
echo ""
echo "Grafana dashboards are available at:"
echo "  - examples/grafana/dashboard.json (full dashboard)"
echo ""
echo "For troubleshooting, see: GRAFANA_INTEGRATION_STRATEGY.md"
echo "=============================================================================="
