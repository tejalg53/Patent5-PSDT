"""
Sprint 5 - Configuration / reference values for the Dynamic Threshold
Characterization Engine (DTCE).

IMPORTANT: Every numeric value in this module is a CONFIGURABLE SIMULATION
BASELINE, chosen to make the DTCE multiplicative model demonstrable and
auditable in the digital twin. None of these numbers are claimed universal
physiological constants. Before any experimental validation section is
finalized, these values must be replaced or justified using published
psychophysical evidence (e.g. peer-reviewed tactile perception literature)
per body zone, frequency band, actuator type, and context.
"""

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# 1. Body-zone baseline threshold (ms) - configurable simulation baseline.
# ---------------------------------------------------------------------------
BASE_THRESHOLDS_MS: Dict[str, float] = {
    "Fingertip": 55.0,
    "Hand": 60.0,
    "Forearm": 65.0,
    "Torso": 70.0,
    "Leg": 65.0,
    "Foot": 50.0,
}

# ---------------------------------------------------------------------------
# 2. Vibration-frequency adjustment factor Ff - configurable prototype bands.
# ---------------------------------------------------------------------------
FREQUENCY_BAND_LOW_HZ = 80.0
FREQUENCY_BAND_HIGH_HZ = 250.0

FREQUENCY_FACTORS = {
    "low": 1.05,       # frequency_hz < FREQUENCY_BAND_LOW_HZ
    "nominal": 1.00,   # FREQUENCY_BAND_LOW_HZ <= frequency_hz <= FREQUENCY_BAND_HIGH_HZ
    "high": 0.95,      # frequency_hz > FREQUENCY_BAND_HIGH_HZ
}


def frequency_factor(frequency_hz: float) -> float:
    """Map a vibration frequency (Hz) to a bounded DTCE adjustment factor.

    Configurable prototype model coefficients only - not a claim about
    universal human vibrotactile physiology.
    """
    if frequency_hz < FREQUENCY_BAND_LOW_HZ:
        return FREQUENCY_FACTORS["low"]
    elif frequency_hz <= FREQUENCY_BAND_HIGH_HZ:
        return FREQUENCY_FACTORS["nominal"]
    else:
        return FREQUENCY_FACTORS["high"]


# ---------------------------------------------------------------------------
# 3. Actuator-type adjustment factor Fa - configurable simulation values.
#    NOTE: this models how stimulus configuration affects perceptual
#    tolerance. It is distinct from actuator *timing delay*, which PEEE
#    (Sprint 6) evaluates separately.
# ---------------------------------------------------------------------------
ACTUATOR_FACTORS: Dict[str, float] = {
    "LRA": 1.00,
    "ERM": 1.05,
    "Piezo": 0.95,
}

# ---------------------------------------------------------------------------
# 4. User Calibration Factor (UCF) - configurable simulation values.
#    We do not implement a QUEST/ZEST psychophysical staircase calibration
#    procedure here; such threshold-measurement methods are known prior
#    art. The novelty being prototyped is what the system does with an
#    already-calibrated threshold, not the calibration procedure itself.
# ---------------------------------------------------------------------------
CALIBRATION_FACTORS: Dict[str, float] = {
    "High Sensitivity": 0.90,
    "Standard": 1.00,
    "Low Sensitivity": 1.10,
}

CUSTOM_CALIBRATION_BOUNDS: Tuple[float, float] = (0.80, 1.20)

# ---------------------------------------------------------------------------
# 5. Motion-state adjustment factor Fm - configurable simulation values.
# ---------------------------------------------------------------------------
MOTION_FACTORS: Dict[str, float] = {
    "Stationary": 1.00,
    "Walking": 1.05,
    "Running": 1.10,
}

# ---------------------------------------------------------------------------
# 6. Environmental-context adjustment factor Fe - configurable simulation
#    values. Kept intentionally simple (three states) for Version 1.0.
# ---------------------------------------------------------------------------
ENVIRONMENT_FACTORS: Dict[str, float] = {
    "Low disturbance": 0.98,
    "Normal": 1.00,
    "High vibration/noise": 1.08,
}
