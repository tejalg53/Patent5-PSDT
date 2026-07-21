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
from typing import Optional
import math


@dataclass(frozen=True)
class PSMResult:
    """Full, human-readable audit trail for one PSMz(t) computation.

    `status` is "OK" for a normal computation, or "INVALID_INPUT" when
    safe_compute_margin() had to reject malformed input without raising.
    All numeric fields are None on an INVALID_INPUT result.
    """

    pt_ms: Optional[float]
    pe_ms: Optional[float]
    psm_ms: Optional[float]
    normalized_psm: Optional[float]
    threshold_utilization_pct: Optional[float]
    margin_sign: Optional[str]
    status: str = "OK"
    error_reason: Optional[str] = None


class PerceptualSynchronizationMarginEngine:
    """Sprint 7: computes PSMz(t) for a single node from its Dynamic
    Perceptual Threshold (PT) and Estimated Perceived Error (PE).

    This engine performs no adaptive control and assigns no
    Relaxed/Nominal/Elevated/Immediate operational state. It only
    characterizes the mathematical synchronization margin itself.
    """

    EPSILON = 1e-9

    def compute_margin(self, pt_ms, pe_ms):
        """Strict computation. Raises ValueError on any invalid input.

        Use this when the caller has already guaranteed valid upstream
        PT/PE (e.g. unit tests exercising the pure equation). Pipeline
        / integration code that must never crash on malformed input
        should call safe_compute_margin() instead.
        """
        if pt_ms is None or pe_ms is None:
            raise ValueError("PT and PE are required.")

        try:
            pt_ms = float(pt_ms)
            pe_ms = float(pe_ms)
        except (TypeError, ValueError):
            raise ValueError("PT and PE must be numeric.")

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
            status="OK",
            error_reason=None,
        )

    def safe_compute_margin(self, pt_ms, pe_ms, node_id=None):
        """Boundary-safe wrapper around compute_margin().

        Never raises. On invalid input (None, PT<=0, NaN/Infinity,
        non-numeric types, negative PE) it returns a PSMResult with
        status="INVALID_INPUT", error_reason set, and every numeric
        field set to None rather than a fabricated number. Intended
        for use by the Coordinator's pipeline so one malformed node
        can never crash a whole simulation cycle.
        """
        try:
            return self.compute_margin(pt_ms, pe_ms)
        except ValueError as exc:
            return PSMResult(
                pt_ms=None,
                pe_ms=None,
                psm_ms=None,
                normalized_psm=None,
                threshold_utilization_pct=None,
                margin_sign=None,
                status="INVALID_INPUT",
                error_reason=str(exc),
            )
