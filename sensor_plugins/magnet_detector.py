"""
Robust magnet detection using Median Absolute Deviation (MAD) with
conditional baseline updates and hysteresis (Schmitt trigger).

Replaces the naive moving average approach which suffered from baseline
drift when a magnet remained near the sensor for extended periods.

Algorithm overview:
1. Collect magnetic field magnitude samples into a baseline buffer
2. Compute the median and MAD (Median Absolute Deviation) of the buffer
3. Convert MAD to a sigma estimate: sigma = MAD * 1.4826 (normal distribution)
4. Compute a robust z-score: |magnitude - median| / sigma
5. Trigger detection when z-score > detection_sigma
6. Release detection when z-score < release_sigma (hysteresis)
7. Only add "clean" (non-detection) readings to the baseline buffer

The conditional update prevents baseline drift when a magnet is present
for a long time. Bi-directional deviation detection handles the unknown
initial state — works whether the magnet starts near or far from the
sensor.
"""

import math
from collections import deque
from typing import Tuple


class MagnetDetector:
    """
    Robust magnet proximity detector using Median Absolute Deviation.

    Uses MAD-based anomaly detection instead of a simple multiplier on
    a moving average. The baseline only updates with clean samples,
    preventing drift when a magnet stays nearby. Hysteresis prevents
    oscillation at detection boundaries.

    Works regardless of initial magnet position because it detects change
    in *either* direction from the established baseline.
    """

    # MAD-to-sigma conversion factor for the normal distribution
    MAD_SCALE_FACTOR = 1.4826
    # Floor for sigma to avoid division-by-zero when readings are near-constant
    MIN_SIGMA = 0.005

    def __init__(
        self,
        baseline_samples: int = 50,
        detection_sigma: float = 5.0,
        release_sigma: float = 3.0,
        min_baseline_samples: int = 10,
    ):
        """
        Initialize magnet detector.

        :param baseline_samples: Maximum number of clean samples kept for baseline
        :param detection_sigma: MAD-sigma threshold to trigger detection
        :param release_sigma: MAD-sigma threshold to release detection (hysteresis)
        :param min_baseline_samples: Minimum clean samples before detection starts
        """
        self.baseline_samples = baseline_samples
        self.detection_sigma = detection_sigma
        self.release_sigma = release_sigma
        self.min_baseline_samples = min_baseline_samples

        self.clean_history: deque = deque(maxlen=baseline_samples)
        self.magnet_detected: bool = False

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _median(data) -> float:
        """Return the median of *data* (non-empty iterable of numbers)."""
        sorted_data = sorted(data)
        n = len(sorted_data)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_data[mid - 1] + sorted_data[mid]) / 2.0
        return float(sorted_data[mid])

    def _calculate_mad(self, data, median: float) -> float:
        """
        Median Absolute Deviation: MAD = median(|x_i - median(x)|).

        :param data: Iterable of numeric samples
        :param median: Pre-computed median of *data*
        :return: MAD value
        """
        deviations = [abs(x - median) for x in data]
        return self._median(deviations)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def update(self, magnitude: float) -> Tuple[bool, float, float]:
        """
        Process a new magnetic-field magnitude reading.

        :param magnitude: Current 3-D magnetic field magnitude (Gauss)
        :return: ``(magnet_detected, baseline, z_score)``
            - *magnet_detected*: ``True`` when a magnet is likely nearby
            - *baseline*: Median of the clean history (robust baseline)
            - *z_score*: Robust z-score of the current reading
        """
        # ----------------------------------------------------------
        # Calibration phase: always accept samples
        # ----------------------------------------------------------
        if len(self.clean_history) < self.min_baseline_samples:
            self.clean_history.append(magnitude)
            baseline = self._median(self.clean_history)
            return False, baseline, 0.0

        # ----------------------------------------------------------
        # Compute robust statistics on the clean baseline
        # ----------------------------------------------------------
        baseline = self._median(self.clean_history)
        mad = self._calculate_mad(self.clean_history, baseline)
        sigma = max(mad * self.MAD_SCALE_FACTOR, self.MIN_SIGMA)

        # Bi-directional robust z-score
        z_score = abs(magnitude - baseline) / sigma

        # ----------------------------------------------------------
        # State machine with hysteresis (Schmitt trigger)
        # ----------------------------------------------------------
        if self.magnet_detected:
            if z_score < self.release_sigma:
                # Field returned to normal — release detection
                self.magnet_detected = False
                self.clean_history.append(magnitude)
        else:
            if z_score > self.detection_sigma:
                # Significant deviation — trigger detection
                self.magnet_detected = True
            else:
                # Normal reading — update baseline
                self.clean_history.append(magnitude)

        return self.magnet_detected, baseline, z_score

    def reset(self) -> None:
        """Clear all state and begin a fresh calibration phase."""
        self.clean_history.clear()
        self.magnet_detected = False
