# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
System information sensor plugins
"""

import subprocess
from typing import Any, Dict

from sensor_plugins.base import SensorPlugin


class IPAddressPlugin(SensorPlugin):
    """Plugin for IP address information"""

    def __init__(self, check_interval: float = 30.0):
        super().__init__("IPAddress", check_interval)

    def _initialize_hardware(self) -> Any:
        """No hardware initialization needed for IP address"""
        return True

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read IP address from system"""
        try:
            # Note: shell=True used with static string (no user input)
            cmd = "hostname -I | cut -d' ' -f1"
            ip = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            if not ip:
                ip = "127.0.0.1"
            return {"ip_address": ip}
        except Exception:
            return {"ip_address": "127.0.0.1"}

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return default IP when unavailable"""
        return {"ip_address": "n/a"}


class CPULoadPlugin(SensorPlugin):
    """Plugin for CPU load information"""

    def __init__(self, check_interval: float = 1.0):
        super().__init__("CPULoad", check_interval)

    def _initialize_hardware(self) -> Any:
        """No hardware initialization needed for CPU load"""
        return True

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read CPU load from system"""
        try:
            # Note: shell=True used with static string (no user input)
            cmd = "top -bn1 | grep load | awk '{printf \"%.2f\", $(NF-2)}'"
            load = subprocess.check_output(cmd, shell=True).decode("utf-8")
            return {"cpu_load": load}
        except Exception:
            return {"cpu_load": "0.50"}

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for CPU load"""
        return {"cpu_load": "n/a"}


class MemoryUsagePlugin(SensorPlugin):
    """Plugin for memory usage information"""

    def __init__(self, check_interval: float = 5.0):
        super().__init__("MemoryUsage", check_interval)

    def _initialize_hardware(self) -> Any:
        """No hardware initialization needed for memory usage"""
        return True

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read memory usage from system"""
        try:
            # Note: shell=True used with static string (no user input)
            cmd = "free -m | awk 'NR==2{printf \"%s/%s MB\", $3,$2}'"
            memory = subprocess.check_output(cmd, shell=True).decode("utf-8")
            return {"memory_usage": memory}
        except Exception:
            return {"memory_usage": "512/2048 MB"}

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for memory usage"""
        return {"memory_usage": "n/a"}
