"""
MQTT virtual sensor plugin
"""

import json
import math
import time
from collections import deque
from typing import Any, Dict, Optional

from sensor_plugins.base import SensorPlugin


class MQTTPlugin(SensorPlugin):
    """Plugin for MQTT virtual sensor that subscribes to sensor data"""

    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic: str = "iot_logger",
        check_interval: float = 5.0,
        burn_in_time: float = 300,
        mag_moving_average_samples: int = 20,
        mag_detection_threshold: float = 2.0,
    ):
        """
        Initialize MQTT sensor plugin
        
        :param broker_host: MQTT broker hostname/IP
        :param broker_port: MQTT broker port
        :param topic: MQTT topic to subscribe to
        :param check_interval: How often to check if MQTT is available
        :param burn_in_time: BME68x burn-in period in seconds
        :param mag_moving_average_samples: Number of samples for magnetic baseline
        :param mag_detection_threshold: Multiplier for magnet detection
        """
        super().__init__("MQTT", check_interval)
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.latest_message = None
        self.message_received = False
        
        # BME68x air quality calculation state
        self.burn_in_time = burn_in_time
        self.start_time = None
        self.burn_in_data = []
        self.gas_baseline = None
        self.hum_baseline = 40.0  # Must be > 0 and < 100
        self.hum_weighting = 0.25
        self.burn_in_complete = False
        
        # MMC5983 magnet detection state
        self.mag_moving_average_samples = mag_moving_average_samples
        self.mag_detection_threshold = mag_detection_threshold
        self.magnitude_history = deque(maxlen=mag_moving_average_samples)
        self.mag_baseline = None

    @property
    def requires_background_updates(self) -> bool:
        """
        MQTT sensor requires background updates to receive messages and maintain
        BME68x burn-in/air quality state.
        
        :return: True - MQTT always needs background updates
        """
        return True

    def _initialize_hardware(self) -> Any:
        """Initialize MQTT client and connect to broker"""
        import paho.mqtt.client as mqtt  # noqa: PLC0415 - Import inside method for optional dependency

        connection_successful = [False]  # Use list to allow modification in callback

        def on_connect(client, userdata, flags, rc):
            """Callback for when client connects to broker"""
            if rc == 0:
                client.subscribe(self.topic)
                connection_successful[0] = True

        def on_message(client, userdata, msg):
            """Callback for when a message is received"""
            try:
                self.latest_message = json.loads(msg.payload.decode())
                self.message_received = True
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        
        # Try to connect with a timeout
        try:
            client.connect(self.broker_host, self.broker_port, keepalive=60)
        except Exception as e:
            error_msg = (
                f"Could not connect to MQTT broker at "
                f"{self.broker_host}:{self.broker_port}: {e}"
            )
            raise RuntimeError(error_msg) from e
        
        # Start the network loop in a background thread
        client.loop_start()
        
        # Wait for connection to be established (with timeout)
        timeout = 5.0  # 5 second timeout
        start = time.time()
        while not connection_successful[0] and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        if not connection_successful[0]:
            client.loop_stop()
            raise RuntimeError(
                f"Timeout waiting for MQTT connection to "
                f"{self.broker_host}:{self.broker_port}. "
                f"Check that broker is running and accessible."
            )
        
        # Initialize BME68x burn-in tracking
        self.start_time = time.time()
        self.burn_in_complete = False
        self.burn_in_data = []
        
        return client

    def _read_sensor_data(self) -> Dict[str, Any]:  # noqa: PLR0914 - Complex sensor data extraction method
        """Read data from latest MQTT message"""
        result = {
            "temperature": "n/a",
            "humidity": "n/a",
            "pressure": "n/a",
            "gas_resistance": "n/a",
            "air_quality": "n/a",
            "light": "n/a",
            "temp_c": "n/a",
            "voltage": "n/a",
            "soc": "n/a",
            "ssid": "n/a",
            "rssi": "n/a",
            "presence_value": "n/a",
            "motion_value": "n/a",
            "sths34_temperature": "n/a",
            "person_detected": "n/a",
            "mag_x": "n/a",
            "mag_y": "n/a",
            "mag_z": "n/a",
            "mag_magnitude": "n/a",
            "mag_temperature": "n/a",
            "magnet_detected": "n/a",
            "mag_baseline": "n/a",
        }

        if not self.message_received or self.latest_message is None:
            return result

        # Extract BME68x data and calculate air quality
        if "BME68x" in self.latest_message:
            bme_data = self.latest_message["BME68x"]
            
            # Get raw sensor values
            if "TemperatureC" in bme_data:
                result["temperature"] = bme_data["TemperatureC"]
            if "Humidity" in bme_data:
                result["humidity"] = bme_data["Humidity"]
            if "Pressure" in bme_data:
                result["pressure"] = bme_data["Pressure"]
            if "Gas Resistance" in bme_data:
                result["gas_resistance"] = bme_data["Gas Resistance"]
            
            # Handle burn-in period for air quality calculation
            curr_time = time.time()
            if not self.burn_in_complete and result["gas_resistance"] != "n/a":
                if curr_time - self.start_time < self.burn_in_time:
                    gas = result["gas_resistance"]
                    self.burn_in_data.append(gas)
                    
                    # Limit burn_in_data to last 50 samples
                    if len(self.burn_in_data) > 50:
                        self.burn_in_data = self.burn_in_data[-50:]
                    
                    result["burn_in_remaining"] = int(
                        self.burn_in_time - (curr_time - self.start_time)
                    )
                elif len(self.burn_in_data) > 0:
                    samples_to_average = self.burn_in_data[-50:]
                    self.gas_baseline = sum(samples_to_average) / len(samples_to_average)
                    self.burn_in_complete = True
                else:
                    # No burn-in data collected - use default
                    self.gas_baseline = 100000
                    self.burn_in_complete = True
            
            # Calculate air quality if burn-in is complete
            if (
                self.burn_in_complete
                and self.gas_baseline
                and result["gas_resistance"] != "n/a"
                and result["humidity"] != "n/a"
            ):
                gas = result["gas_resistance"]
                gas_offset = self.gas_baseline - gas
                
                hum = result["humidity"]
                hum_offset = hum - self.hum_baseline
                
                # Calculate humidity score
                if hum_offset > 0:
                    denominator = 100 - self.hum_baseline
                    if denominator > 0:
                        hum_score = (100 - self.hum_baseline - hum_offset) / (
                            100 - self.hum_baseline
                        )
                        hum_score *= self.hum_weighting * 100
                    else:
                        hum_score = 0
                elif self.hum_baseline > 0:
                    hum_score = (self.hum_baseline + hum_offset) / self.hum_baseline
                    hum_score *= self.hum_weighting * 100
                else:
                    hum_score = 0
                
                # Calculate gas score
                if gas_offset > 0 and self.gas_baseline > 0:
                    gas_score = (gas / self.gas_baseline) * (
                        100 - (self.hum_weighting * 100)
                    )
                else:
                    gas_score = 100 - (self.hum_weighting * 100)
                
                result["air_quality"] = hum_score + gas_score

        # Extract VEML7700 data
        if "VEML7700" in self.latest_message:
            veml_data = self.latest_message["VEML7700"]
            if "Lux" in veml_data:
                result["light"] = veml_data["Lux"]

        # Extract TMP117 data
        if "TMP117" in self.latest_message:
            tmp_data = self.latest_message["TMP117"]
            if "Temperature (C)" in tmp_data:
                result["temp_c"] = tmp_data["Temperature (C)"]

        # Extract MAX17048 data
        if "MAX17048" in self.latest_message:
            max_data = self.latest_message["MAX17048"]
            if "Voltage (V)" in max_data:
                result["voltage"] = max_data["Voltage (V)"]
            if "State Of Charge (%)" in max_data:
                result["soc"] = max_data["State Of Charge (%)"]

        # Extract System Info
        if "System Info" in self.latest_message:
            sys_data = self.latest_message["System Info"]
            if "SSID" in sys_data:
                result["ssid"] = sys_data["SSID"]
            if "RSSI" in sys_data:
                result["rssi"] = sys_data["RSSI"]

        # Extract STHS34PF80 data
        if "STHS34PF80" in self.latest_message:
            sths_data = self.latest_message["STHS34PF80"]
            if "Presence (cm^-1)" in sths_data:
                result["presence_value"] = sths_data["Presence (cm^-1)"]
            if "Motion (LSB)" in sths_data:
                result["motion_value"] = sths_data["Motion (LSB)"]
            if "Temperature (C)" in sths_data:
                result["sths34_temperature"] = sths_data["Temperature (C)"]
            
            # Calculate person detection status
            # Person is detected if presence value >= 1000 OR motion value > 0
            # Using same threshold as STHS34PF80Plugin default
            presence_threshold = 1000
            if result["presence_value"] != "n/a" and result["motion_value"] != "n/a":
                presence_detected = result["presence_value"] >= presence_threshold
                motion_detected = result["motion_value"] > 0
                result["person_detected"] = presence_detected or motion_detected
            elif result["presence_value"] != "n/a":
                result["person_detected"] = result["presence_value"] >= presence_threshold
            elif result["motion_value"] != "n/a":
                result["person_detected"] = result["motion_value"] > 0

        # Extract MMC5983 magnetometer data
        if "MMC5983" in self.latest_message:
            mmc_data = self.latest_message["MMC5983"]
            if "X Field (Gauss)" in mmc_data:
                result["mag_x"] = mmc_data["X Field (Gauss)"]
            if "Y Field (Gauss)" in mmc_data:
                result["mag_y"] = mmc_data["Y Field (Gauss)"]
            if "Z Field (Gauss)" in mmc_data:
                result["mag_z"] = mmc_data["Z Field (Gauss)"]
            if "Temperature (C)" in mmc_data:
                result["mag_temperature"] = mmc_data["Temperature (C)"]
            
            # Calculate magnitude and detect magnet if we have all 3 axes
            if (
                result["mag_x"] != "n/a"
                and result["mag_y"] != "n/a"
                and result["mag_z"] != "n/a"
            ):
                # Calculate 3D magnitude
                magnitude = math.sqrt(
                    result["mag_x"] ** 2
                    + result["mag_y"] ** 2
                    + result["mag_z"] ** 2
                )
                result["mag_magnitude"] = magnitude
                
                # Update moving average baseline
                self.magnitude_history.append(magnitude)
                if len(self.magnitude_history) > 0:
                    self.mag_baseline = sum(self.magnitude_history) / len(
                        self.magnitude_history
                    )
                    result["mag_baseline"] = self.mag_baseline
                
                # Detect magnet based on deviation from baseline
                if self.mag_baseline is not None:
                    result["magnet_detected"] = (
                        magnitude > self.mag_baseline * self.mag_detection_threshold
                    )

        return result

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for all sensor values"""
        return {
            "temperature": "n/a",
            "humidity": "n/a",
            "pressure": "n/a",
            "gas_resistance": "n/a",
            "air_quality": "n/a",
            "light": "n/a",
            "temp_c": "n/a",
            "voltage": "n/a",
            "soc": "n/a",
            "ssid": "n/a",
            "rssi": "n/a",
            "presence_value": "n/a",
            "motion_value": "n/a",
            "sths34_temperature": "n/a",
            "person_detected": "n/a",
            "mag_x": "n/a",
            "mag_y": "n/a",
            "mag_z": "n/a",
            "mag_magnitude": "n/a",
            "mag_temperature": "n/a",
            "magnet_detected": "n/a",
            "mag_baseline": "n/a",
        }

    def format_display(self, data: Dict[str, Any]) -> str:
        """Format sensor data for display"""
        burn_in_remaining = data.get("burn_in_remaining")
        air_quality = data.get("air_quality", "n/a")

        if burn_in_remaining is not None:
            return f"MQTT Burn-in: {burn_in_remaining}s"
        elif air_quality != "n/a":
            return f"MQTT AirQ: {air_quality:.1f}"
        else:
            return "MQTT: n/a"

    def __del__(self):
        """Cleanup MQTT connection"""
        if self.sensor_instance is not None:
            try:
                self.sensor_instance.loop_stop()
                self.sensor_instance.disconnect()
            except Exception:
                pass
