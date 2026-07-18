"""
Sprint 5 - Dynamic Threshold Characterization Engine (DTCE).

Computes a time-varying, body-zone-specific Dynamic Perceptual Threshold
PTz(t) for a haptic node using a transparent, auditable multiplicative
adjustment model:

    PTz(t) = PTbase,z x Ff x Fa x UCF x Fm x Fe

All coefficients used here come from threshold_profiles.py, which labels
them explicitly as CONFIGURABLE SIMULATION BASELINE VALUES, not claimed
universal physiological constants.

This module intentionally does NOT compute Perceived Error (PE) or the
Perceptual Synchronization Margin (PSM), and does NOT assign a
Relaxed/Nominal/Elevated/Immediate synchronization state. Those remain
the responsibility of later sprints.
"""

from dataclasses import dataclass
from typing import Optional

from .threshold_profiles import (
    BASE_THRESHOLDS_MS,
    ACTUATOR_FACTORS,
    CALIBRATION_FACTORS,
    CUSTOM_CALIBRATION_BOUNDS,
    MOTION_FACTORS,
    ENVIRONMENT_FACTORS,
    frequency_factor,
)


@dataclass
class DTCEAudit:
    """Full, human-readable audit trail for one PTz(t) computation."""

    body_zone: str
    base_pt_ms: float

    frequency_hz: float
    frequency_factor: float

    actuator_type: str
    actuator_factor: float

    calibration_profile: str
    calibration_factor: float

    motion_state: str
    motion_factor: float

    environment_state: str
    environment_factor: float

    dynamic_pt_ms: float


class DynamicThresholdCharacterizationEngine:
    """Sprint 5: computes PTz(t) for a single node from six labeled inputs.

    This engine performs no adaptive control and makes no claims about
    Perceived Error, PSM, or synchronization state. It only characterizes
    the dynamic perceptual threshold itself.
    """

    def compute_threshold(
        self,
        body_zone: str,
        frequency_hz: float,
        actuator_type: str,
        calibration_profile: str = "Standard",
        custom_calibration_factor: Optional[float] = None,
        motion_state: str = "Stationary",
        environment_state: str = "Normal",
    ) -> DTCEAudit:
        if body_zone not in BASE_THRESHOLDS_MS:
            raise ValueError(f"Unsupported body zone for DTCE: {body_zone!r}")
        if actuator_type not in ACTUATOR_FACTORS:
            raise ValueError(f"Unsupported actuator type for DTCE: {actuator_type!r}")
        if motion_state not in MOTION_FACTORS:
            raise ValueError(f"Unsupported motion state for DTCE: {motion_state!r}")
        if environment_state not in ENVIRONMENT_FACTORS:
            raise ValueError(f"Unsupported environment state for DTCE: {environment_state!r}")
        if frequency_hz is None or frequency_hz < 0:
            raise ValueError(f"Invalid vibration frequency for DTCE: {frequency_hz!r}")

        base_pt = BASE_THRESHOLDS_MS[body_zone]
        f_factor = frequency_factor(frequency_hz)
        a_factor = ACTUATOR_FACTORS[actuator_type]
        m_factor = MOTION_FACTORS[motion_state]
        e_factor = ENVIRONMENT_FACTORS[environment_state]

        if calibration_profile == "Custom":
            if custom_calibration_factor is None:
                raise ValueError("Custom calibration profile requires custom_calibration_factor.")
            lo, hi = CUSTOM_CALIBRATION_BOUNDS
            ucf = max(lo, min(hi, float(custom_calibration_factor)))
        elif calibration_profile in CALIBRATION_FACTORS:
            ucf = CALIBRATION_FACTORS[calibration_profile]
        else:
            raise ValueError(f"Unsupported calibration profile for DTCE: {calibration_profile!r}")

        dynamic_pt = base_pt * f_factor * a_factor * ucf * m_factor * e_factor

        return DTCEAudit(
            body_zone=body_zone,
            base_pt_ms=base_pt,
            frequency_hz=frequency_hz,
            frequency_factor=f_factor,
            actuator_type=actuator_type,
            actuator_factor=a_factor,
            calibration_profile=calibration_profile,
            calibration_factor=ucf,
            motion_state=motion_state,
            motion_factor=m_factor,
            environment_state=environment_state,
            environment_factor=e_factor,
            dynamic_pt_ms=dynamic_pt,
        )
