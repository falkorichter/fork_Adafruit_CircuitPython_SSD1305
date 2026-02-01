"""
System information sensor plugins
"""

import socket
from typing import Any, Dict

from sensor_plugins.base import SensorPlugin

# Try to use psutil for better performance, fallback to defaults if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


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
            # Use socket to get local IP - much faster and safer than subprocess
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            try:
                # Connect to external address to determine local IP
                # This doesn't actually send data
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
            finally:
                s.close()
            
            if not ip or ip == "0.0.0.0":
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
        if HAS_PSUTIL:
            try:
                # Use psutil - much faster and safer than subprocess
                load = psutil.getloadavg()[0]  # 1-minute load average
                return {"cpu_load": f"{load:.2f}"}
            except Exception:
                return {"cpu_load": "0.50"}
        else:
            # psutil not available - return default
            return {"cpu_load": "n/a"}

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
        if HAS_PSUTIL:
            try:
                # Use psutil - much faster and safer than subprocess
                mem = psutil.virtual_memory()
                used_mb = mem.used // (1024 * 1024)
                total_mb = mem.total // (1024 * 1024)
                return {"memory_usage": f"{used_mb}/{total_mb} MB"}
            except Exception:
                return {"memory_usage": "512/2048 MB"}
        else:
            # psutil not available - return default
            return {"memory_usage": "n/a"}

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for memory usage"""
        return {"memory_usage": "n/a"}
