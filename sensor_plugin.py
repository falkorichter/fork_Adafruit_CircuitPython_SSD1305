# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Sensor plugin system for hot-pluggable sensor support

.. deprecated::
    This module is deprecated. Import from `sensor_plugins` package instead:
    
    Instead of:
        from sensor_plugin import SensorPlugin, TMP117Plugin
    
    Use:
        from sensor_plugins import SensorPlugin, TMP117Plugin

This file maintained for backward compatibility. All classes have been moved to
the sensor_plugins package with the following structure:
    - sensor_plugins.base.SensorPlugin
    - sensor_plugins.tmp117_plugin.TMP117Plugin
    - sensor_plugins.veml7700_plugin.VEML7700Plugin
    - sensor_plugins.bme680_plugin.BME680Plugin
"""

# Import all classes for backward compatibility
from sensor_plugins import BME680Plugin, SensorPlugin, TMP117Plugin, VEML7700Plugin

__all__ = ["SensorPlugin", "TMP117Plugin", "BME680Plugin", "VEML7700Plugin"]

