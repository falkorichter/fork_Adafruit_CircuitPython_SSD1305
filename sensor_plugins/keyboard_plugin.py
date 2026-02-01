"""
Keyboard sensor plugin - tracks last 5 characters entered
"""

import select
import threading
from collections import deque
from typing import Any, Dict

from sensor_plugins.base import SensorPlugin


class KeyboardPlugin(SensorPlugin):
    """Plugin for keyboard input tracking using evdev"""

    def __init__(self, check_interval: float = 0.1):
        super().__init__("Keyboard", check_interval)
        self.key_buffer = deque(maxlen=5)  # Store last 5 characters
        self.listener_thread = None
        self.running = False
        self._lock = threading.Lock()
        self.keyboards = []

    def _initialize_hardware(self) -> Any:
        """Initialize evdev keyboard listener"""
        import evdev  # noqa: PLC0415 - Import inside method for optional dependency

        # Find keyboard devices
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        self.keyboards = []
        for device in devices:
            # Check if device has key capabilities (is a keyboard)
            caps = device.capabilities(verbose=False)
            if 1 in caps:  # EV_KEY
                # Check if it has actual keyboard keys
                keys = caps[1]
                if any(k in range(1, 128) for k in keys):
                    self.keyboards.append(device)

        if not self.keyboards:
            raise RuntimeError("No keyboard devices found")

        # Start listener thread
        self.running = True
        self.listener_thread = threading.Thread(target=self._listen_keyboard, daemon=True)
        self.listener_thread.start()

        return self.keyboards

    def _process_keyboard_event(self, evdev, event, key_map):
        """Process a single keyboard event and add character to buffer if applicable"""
        # Only process key press events (not release)
        if event.type != evdev.ecodes.EV_KEY:
            return

        # Only on key press (value=1), not release (value=0)
        if event.value != 1:
            return

        # Map key code to character
        char = key_map.get(event.code)
        if char:
            with self._lock:
                self.key_buffer.append(char)

    def _listen_keyboard(self):
        """Background thread to listen for keyboard events"""
        try:
            import evdev  # noqa: PLC0415

            # Character mapping for common keys
            key_map = {
                evdev.ecodes.KEY_A: "a",
                evdev.ecodes.KEY_B: "b",
                evdev.ecodes.KEY_C: "c",
                evdev.ecodes.KEY_D: "d",
                evdev.ecodes.KEY_E: "e",
                evdev.ecodes.KEY_F: "f",
                evdev.ecodes.KEY_G: "g",
                evdev.ecodes.KEY_H: "h",
                evdev.ecodes.KEY_I: "i",
                evdev.ecodes.KEY_J: "j",
                evdev.ecodes.KEY_K: "k",
                evdev.ecodes.KEY_L: "l",
                evdev.ecodes.KEY_M: "m",
                evdev.ecodes.KEY_N: "n",
                evdev.ecodes.KEY_O: "o",
                evdev.ecodes.KEY_P: "p",
                evdev.ecodes.KEY_Q: "q",
                evdev.ecodes.KEY_R: "r",
                evdev.ecodes.KEY_S: "s",
                evdev.ecodes.KEY_T: "t",
                evdev.ecodes.KEY_U: "u",
                evdev.ecodes.KEY_V: "v",
                evdev.ecodes.KEY_W: "w",
                evdev.ecodes.KEY_X: "x",
                evdev.ecodes.KEY_Y: "y",
                evdev.ecodes.KEY_Z: "z",
                evdev.ecodes.KEY_0: "0",
                evdev.ecodes.KEY_1: "1",
                evdev.ecodes.KEY_2: "2",
                evdev.ecodes.KEY_3: "3",
                evdev.ecodes.KEY_4: "4",
                evdev.ecodes.KEY_5: "5",
                evdev.ecodes.KEY_6: "6",
                evdev.ecodes.KEY_7: "7",
                evdev.ecodes.KEY_8: "8",
                evdev.ecodes.KEY_9: "9",
                evdev.ecodes.KEY_SPACE: " ",
            }

            # Monitor all keyboard devices using select (non-blocking)
            while self.running:
                # Use select to wait for events from any keyboard
                r, w, x = select.select(self.keyboards, [], [], 0.5)
                for device in r:
                    try:
                        # Read events from this device
                        for event in device.read():
                            self._process_keyboard_event(evdev, event, key_map)
                    except OSError:
                        # Device disconnected, continue with other devices
                        pass
        except Exception:
            # If listener fails, stop gracefully
            self.running = False

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read last 5 characters from keyboard buffer"""
        with self._lock:
            chars = "".join(self.key_buffer)
        return {"last_keys": chars}

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for keyboard data"""
        return {"last_keys": "n/a"}

    def format_display(self, data: Dict[str, Any]) -> str:
        """Format keyboard data for display (right-aligned)"""
        keys = data.get("last_keys", "n/a")
        if keys == "n/a":
            return "Keys: n/a"
        elif not keys:
            return "Keys: _____"
        else:
            # Pad to 5 characters for consistent display
            return f"Keys: {keys:>5s}"
