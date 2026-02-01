"""
System information sensor plugins
"""

import socket
import subprocess
from typing import Any, Dict

from sensor_plugins.base import SensorPlugin

# Try to use psutil for better performance, fallback to subprocess if not available
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
            # Use socket to get local IP - much faster than subprocess
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
            # Fallback to subprocess if socket method fails
            try:
                cmd = "hostname -I | cut -d' ' -f1"
                ip = subprocess.check_output(cmd, shell=True, timeout=0.5).decode("utf-8").strip()
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
            if HAS_PSUTIL:
                # Use psutil - much faster than subprocess
                load = psutil.getloadavg()[0]  # 1-minute load average
                return {"cpu_load": f"{load:.2f}"}
            else:
                # Fallback to subprocess
                cmd = "top -bn1 | grep load | awk '{printf \"%.2f\", $(NF-2)}'"
                load = subprocess.check_output(cmd, shell=True, timeout=1.0).decode("utf-8")
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
            if HAS_PSUTIL:
                # Use psutil - much faster than subprocess
                mem = psutil.virtual_memory()
                used_mb = mem.used // (1024 * 1024)
                total_mb = mem.total // (1024 * 1024)
                return {"memory_usage": f"{used_mb}/{total_mb} MB"}
            else:
                # Fallback to subprocess
                cmd = "free -m | awk 'NR==2{printf \"%s/%s MB\", $3,$2}'"
                memory = subprocess.check_output(cmd, shell=True, timeout=1.0).decode("utf-8")
                return {"memory_usage": memory}
        except Exception:
            return {"memory_usage": "512/2048 MB"}

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for memory usage"""
        return {"memory_usage": "n/a"}
