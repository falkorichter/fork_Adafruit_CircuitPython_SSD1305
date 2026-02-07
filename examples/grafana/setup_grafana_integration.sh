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

INFLUX_ALREADY_SETUP=false

if command -v influxd &> /dev/null; then
    # Check if this is InfluxDB 1.x or 2.x
    if [ -f /etc/influxdb/influxdb.conf ]; then
        print_error "InfluxDB 1.x detected (config at /etc/influxdb/influxdb.conf)"
        print_error "This script requires InfluxDB 2.x. Please uninstall InfluxDB 1.x first:"
        print_error "  sudo apt-get remove influxdb"
        print_error "  sudo rm -rf /etc/influxdb"
        print_error "Then run this script again."
        exit 1
    fi
    
    print_warn "InfluxDB is already installed. Skipping installation."
    INFLUX_ALREADY_SETUP=true
else
    print_info "Adding InfluxDB repository..."
    
    # Add InfluxDB GPG key and repository
    wget -q https://repos.influxdata.com/influxdata-archive_compat.key -O /tmp/influxdata-archive_compat.key
    echo '393e8779c89ac8d958f81f942f9ad7fb82a25e133faddaf92e15b16e6ac9ce4c /tmp/influxdata-archive_compat.key' | sha256sum -c && cat /tmp/influxdata-archive_compat.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg > /dev/null
    
    echo 'deb [signed-by=/etc/apt/trusted.gpg.d/influxdata-archive_compat.gpg] https://repos.influxdata.com/debian stable main' | sudo tee /etc/apt/sources.list.d/influxdata.list
    
    print_info "Updating package list..."
    sudo apt-get update -qq
    
    print_info "Installing InfluxDB 2.x (this may take a few minutes)..."
    if ! sudo apt-get install -y influxdb2; then
        print_error "Failed to install InfluxDB"
        print_error "Please check your internet connection and try again"
        exit 1
    fi
    
    print_info "Enabling and starting InfluxDB service..."
    sudo systemctl enable influxdb
    sudo systemctl start influxdb
    
    # Wait for InfluxDB to start
    print_info "Waiting for InfluxDB to start..."
    sleep 10
    
    print_info "InfluxDB installed successfully!"
fi

# Install InfluxDB CLI tools if not present
if ! command -v influx &> /dev/null; then
    print_info "Installing InfluxDB CLI tools..."
    
    # Repository should already be added from above
    if ! sudo apt-get install -y influxdb2-cli; then
        print_error "Failed to install InfluxDB CLI tools"
        print_error "Trying to continue anyway..."
    else
        print_info "InfluxDB CLI tools installed successfully!"
    fi
fi

# Verify we have the influx command
if ! command -v influx &> /dev/null; then
    print_error "The 'influx' CLI command is not available"
    print_error "Please install it manually: sudo apt-get install influxdb2-cli"
    exit 1
fi

# =============================================================================
# Step 1.5: Automated InfluxDB Setup (CLI-based, no manual intervention)
# =============================================================================

print_info "Configuring InfluxDB..."

# Check if InfluxDB is already configured
if influx ping &> /dev/null && influx auth list &> /dev/null 2>&1; then
    print_warn "InfluxDB appears to be already configured"
    print_info "Attempting to retrieve existing configuration..."
    
    # Try to get existing token from influx CLI config
    if [ -f ~/.influxdbv2/configs ]; then
        INFLUX_TOKEN=$(grep -m 1 "token = " ~/.influxdbv2/configs | cut -d'"' -f2)
        if [ -n "$INFLUX_TOKEN" ]; then
            print_info "Found existing InfluxDB token"
        else
            print_warn "Could not find token in config file"
            echo ""
            print_warn "Please enter your existing InfluxDB token:"
            read -r INFLUX_TOKEN
        fi
    else
        print_warn "No InfluxDB config found"
        echo ""
        print_warn "Please enter your existing InfluxDB token:"
        read -r INFLUX_TOKEN
    fi
else
    # Perform automated setup
    print_info "Running automated InfluxDB setup..."
    
    # Generate a secure random password
    INFLUX_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    # Set up InfluxDB with CLI
    print_info "Creating initial configuration..."
    influx setup \
        --username admin \
        --password "$INFLUX_PASSWORD" \
        --org sensors \
        --bucket sensor_data \
        --retention 0 \
        --force \
        --json > /tmp/influx_setup.json 2>&1
    
    if [ $? -eq 0 ]; then
        print_info "InfluxDB setup completed successfully!"
        
        # Extract token from setup output
        INFLUX_TOKEN=$(cat /tmp/influx_setup.json | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
        
        if [ -z "$INFLUX_TOKEN" ]; then
            # Try alternative extraction method
            INFLUX_TOKEN=$(influx auth list --json 2>/dev/null | grep -o '"token":"[^"]*"' | head -1 | cut -d'"' -f4)
        fi
        
        if [ -n "$INFLUX_TOKEN" ]; then
            print_info "InfluxDB token generated successfully"
            
            # Save credentials to a file for reference
            cat > ~/influxdb_credentials.txt << EOF
InfluxDB Credentials
====================
URL: http://localhost:8086
Username: admin
Password: $INFLUX_PASSWORD
Organization: sensors
Bucket: sensor_data
Token: $INFLUX_TOKEN

IMPORTANT: Keep this file secure and delete it after noting the credentials!
EOF
            chmod 600 ~/influxdb_credentials.txt
            
            print_warn "Credentials saved to: ~/influxdb_credentials.txt"
            print_warn "Please store these credentials securely and delete the file!"
        else
            print_error "Failed to extract InfluxDB token"
            print_error "Please set up InfluxDB manually and run this script again"
            exit 1
        fi
        
        # Clean up setup output
        rm -f /tmp/influx_setup.json
    else
        print_error "InfluxDB setup failed"
        cat /tmp/influx_setup.json
        exit 1
    fi
fi

if [ -z "$INFLUX_TOKEN" ]; then
    print_error "No InfluxDB token available"
    exit 1
fi

# =============================================================================
# Step 2: Install Telegraf
# =============================================================================

print_info "Installing Telegraf..."

if command -v telegraf &> /dev/null; then
    print_warn "Telegraf is already installed. Skipping installation."
else
    # Repository should already be added from InfluxDB installation
    print_info "Installing Telegraf from repository (this may take a few minutes)..."
    
    if ! sudo apt-get install -y telegraf; then
        print_error "Failed to install Telegraf"
        print_error "Please check your internet connection and try again"
        exit 1
    fi
    
    print_info "Telegraf installed successfully!"
fi

# =============================================================================
# Step 3: Configure Telegraf
# =============================================================================

print_info "Configuring Telegraf..."

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
echo "       - Token: $INFLUX_TOKEN"
echo "       - Default Bucket: sensor_data"
echo "  4. Import dashboard from examples/grafana/dashboard.json"
echo ""
if [ -f ~/influxdb_credentials.txt ]; then
    echo "InfluxDB credentials saved to: ~/influxdb_credentials.txt"
    echo "  - Please store these credentials securely"
    echo "  - Delete the file after noting the credentials"
    echo ""
fi
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
