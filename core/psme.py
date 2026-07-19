"""
Sprint 7 - Perceptual Synchronization Margin Engine (PSME).

Computes the Perceptual Synchronization Margin PSMz(t) for a haptic node
from two already-computed upstream quantities:

    PTz(t) - Dynamic Perceptual Threshold, produced by the DTCE (Sprint 5)
    PEz(t) - Estimated Perceived Synchronization Error, produced by
    the PEEE (Sprint 6)

    PSMz(t) = PTz(t) - PEz(t)
    NPSMz(t) = PSMz(t) / PTz(t)
    TUz(t) = (PEz(t) / PTz(t)) * 100

PSM is intentionally signed. A negative PSM (PE exceeds PT) is a valid,
meaningful result and must never be clamped to zero. This engine only
identifies the mathematical sign of the margin (POSITIVE / BOUNDARY /
NEGATIVE); it makes no operational or safety classification (that is
the responsibility of a later sprint's SCE).
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PSMResult:
    """Full, human-readable audit trail for one PSMz(t) computation."""

    pt_ms: float
    pe_ms: float
    psm_ms: float
    normalized_psm: float
    threshold_utilization_pct: float
    margin_sign: str


class PerceptualSynchronizationMarginEngine:
    """Sprint 7: computes PSMz(t) for a single node from its Dynamic
    Perceptual Threshold (PT) and Estimated Perceived Error (PE).

    This engine performs no adaptive control and assigns no
    Relaxed/Nominal/Elevated/Immediate operational state. It only
    characterizes the mathematical synchronization margin itself.
    """

    EPSILON = 1e-9

    def compute_margin(self, pt_ms, pe_ms):
        if pt_ms is None or pe_ms is None:
            raise ValueError("PT and PE are required.")

        pt_ms = float(pt_ms)
        pe_ms = float(pe_ms)

        if not math.isfinite(pt_ms) or not math.isfinite(pe_ms):
            raise ValueError("PT and PE must be finite.")

        if pt_ms <= 0:
            raise ValueError("PT must be greater than zero.")

        if pe_ms < 0:
            raise ValueError("PE cannot be negative.")

        psm_ms = pt_ms - pe_ms
        normalized_psm = psm_ms / pt_ms
        threshold_utilization_pct = (pe_ms / pt_ms) * 100.0

        if abs(psm_ms) <= self.EPSILON:
            margin_sign = "BOUNDARY"
        elif psm_ms > 0:
            margin_sign = "POSITIVE"
        else:
            margin_sign = "NEGATIVE"

        return PSMResult(
            pt_ms=pt_ms,
            pe_ms=pe_ms,
            psm_ms=psm_ms,
            normalized_psm=normalized_psm,
            threshold_utilization_pct=threshold_utilization_pct,
            margin_sign=margin_sign,
        )
