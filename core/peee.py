"""
Sprint 6 - Perceived Error Estimation Engine (PEEE).

Computes an ESTIMATED PERCEIVED SYNCHRONIZATION ERROR PEz(t) for a haptic
node, derived from four RESIDUAL/DIFFERENTIAL timing contributors:

    CDz(t) - Clock Drift Contribution
    NDz(t) - Network Delay Contribution (residual vs. a reference delay)
    ADz(t) - Actuator Driver Delay Contribution
    MDz(t) - Mechanical Startup Delay Contribution

Design intent (important, do not weaken elsewhere): PE is meant to
represent EFFECTIVE timing misalignment relevant to inter-node
synchronization, not the blind sum of every absolute latency in the
system. A delay that is common to every node shifts the whole haptic
event in time but does not, by itself, make two nodes feel out of sync
with each other. That is why NDz(t) here is a residual relative to a
reference/expected delay rather than the raw measured delay.

Framing note (do not weaken): this is an ESTIMATED PERCEIVED
SYNCHRONIZATION ERROR derived from residual timing contributions
affecting the temporal delivery of haptic actuation - not a claim that
human perceived error is simply CD + ND + AD + MD in an absolute
physiological sense, and not the same quantity as raw end-to-end latency.

This module intentionally does NOT compute the Perceptual Synchronization
Margin (PSM) or assign a Relaxed/Nominal/Elevated/Immediate state. Those
remain the responsibility of PSME (Sprint 7). It also performs no
resynchronization (clock reset) control logic; that belongs to a later
sprint.

All coefficients, bounds, and profiles used here come from
error_profiles.py, which labels them explicitly as CONFIGURABLE SIMULATION
ASSUMPTIONS, not claimed manufacturer specifications.
"""

import random
from dataclasses import dataclass
from typing import Dict, Optional

from .error_profiles import (
    PE_MODELS,
    DEFAULT_PE_MODEL,
    DEFAULT_WEIGHTS,
    WEIGHT_BOUNDS,
    CLOCK_DRIFT_BOUNDS_MS,
    CLOCK_DRIFT_GROWTH_MS_PER_S,
    NETWORK_REFERENCE_DELAY_MS,
    NETWORK_RESIDUAL_BOUNDS_MS,
    NETWORK_CONDITION_ADJUSTMENT_MS,
    DEFAULT_NETWORK_CONDITION,
    NETWORK_JITTER_STD_MS,
    NETWORK_DELAY_BOUNDS_MS,
    ACTUATOR_AD_PROFILE_FACTOR,
    AD_BOUNDS_MS,
    AD_JITTER_STD_MS,
    ACTUATOR_MD_PROFILE_FACTOR,
    MD_BOUNDS_MS,
    MD_JITTER_STD_MS,
)


def _clamp(value: float, bounds) -> float:
    lo, hi = bounds
    return max(lo, min(hi, value))


@dataclass
class PEEEAudit:
    """Full, human-readable audit trail for one PEz(t) computation."""

    node_id: Optional[str]
    body_zone: Optional[str]

    cd_ms: float
    nd_ms: float
    ad_ms: float
    md_ms: float

    model: str

    weight_cd: float
    weight_nd: float
    weight_ad: float
    weight_md: float

    contribution_cd: float
    contribution_nd: float
    contribution_ad: float
    contribution_md: float

    perceived_error_ms: float


class PerceivedErrorEstimationEngine:
    """Sprint 6: computes PEz(t) for a single node from four labeled,
    already-resolved residual timing contributors (CD, ND, AD, MD).

    This engine performs no adaptive control and makes no claims about
    PSM or synchronization state.
    """

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self._node_rngs: Dict[str, random.Random] = {}

    def _rng_for(self, node_id: str) -> random.Random:
        """Deterministic per-node RNG stream, so seeded runs stay
        reproducible regardless of call order across nodes."""
        if node_id not in self._node_rngs:
            self._node_rngs[node_id] = random.Random(f"{self.seed}:{node_id}")
        return self._node_rngs[node_id]

    # ------------------------------------------------------------------
    # Component resolution helpers - turn a node's raw simulated
    # measurements into the four residual/differential contributors that
    # compute_error() combines. Kept separate from compute_error() so the
    # combination math stays a pure, easily-testable function of already
    # resolved millisecond values (matches the required class contract).
    # ------------------------------------------------------------------
    def resolve_clock_drift_ms(self, raw_clock_drift_ms: float) -> float:
        """CDz(t) = |clock error| relative to the reference clock."""
        cd = abs(raw_clock_drift_ms)
        return _clamp(cd, CLOCK_DRIFT_BOUNDS_MS)

    def resolve_network_residual_ms(
        self,
        measured_network_delay_ms: float,
        network_condition: str = DEFAULT_NETWORK_CONDITION,
    ) -> float:
        """NDz(t) = residual delay relative to a reference/expected delay,
        not the raw measured delay. A simulated network condition shifts
        the measured delay before the residual is taken."""
        adjustment = NETWORK_CONDITION_ADJUSTMENT_MS.get(
            network_condition, NETWORK_CONDITION_ADJUSTMENT_MS[DEFAULT_NETWORK_CONDITION]
        )
        adjusted_measured = max(0.0, measured_network_delay_ms + adjustment)
        residual = max(0.0, adjusted_measured - NETWORK_REFERENCE_DELAY_MS)
        return _clamp(residual, NETWORK_RESIDUAL_BOUNDS_MS)

    def resolve_actuator_driver_delay_ms(
        self, raw_actuator_driver_delay_ms: float, actuator_type: str
    ) -> float:
        """ADz(t): the node's simulated electrical driver delay, adjusted
        by a configurable per-actuator-type profile factor."""
        factor = ACTUATOR_AD_PROFILE_FACTOR.get(actuator_type, 1.0)
        return _clamp(raw_actuator_driver_delay_ms * factor, AD_BOUNDS_MS)

    def resolve_mechanical_startup_delay_ms(
        self, raw_mechanical_startup_delay_ms: float, actuator_type: str
    ) -> float:
        """MDz(t): the node's simulated mechanical startup delay, adjusted
        by a configurable per-actuator-type profile factor."""
        factor = ACTUATOR_MD_PROFILE_FACTOR.get(actuator_type, 1.0)
        return _clamp(raw_mechanical_startup_delay_ms * factor, MD_BOUNDS_MS)

    # ------------------------------------------------------------------
    # Core computation.
    # ------------------------------------------------------------------
    def compute_error(
        self,
        clock_drift_ms,
        network_residual_ms,
        actuator_driver_delay_ms,
        mechanical_startup_delay_ms,
        model=DEFAULT_PE_MODEL,
        weights=None,
        node_id=None,
        body_zone=None,
    ) -> PEEEAudit:
        """Combine four already-resolved residual contributions (ms) into
        a single estimated Perceived Synchronization Error PEz(t).

        model="additive" -> PE = CD + ND + AD + MD (all weights = 1.0)
        model="weighted" -> PE = wCD*CD + wND*ND + wAD*AD + wMD*MD
        """
        if model not in PE_MODELS:
            raise ValueError(f"Unsupported PE model: {model!r}")

        components = {
            "CD": clock_drift_ms,
            "ND": network_residual_ms,
            "AD": actuator_driver_delay_ms,
            "MD": mechanical_startup_delay_ms,
        }
        for name, value in components.items():
            if value is None or value < 0:
                raise ValueError(f"Negative or missing {name} passed to PEEE: {value!r}")

        if model == "additive":
            resolved_weights = {"CD": 1.0, "ND": 1.0, "AD": 1.0, "MD": 1.0}
        else:
            resolved_weights = dict(DEFAULT_WEIGHTS)
            if weights:
                for key in resolved_weights:
                    if key in weights and weights[key] is not None:
                        resolved_weights[key] = _clamp(float(weights[key]), WEIGHT_BOUNDS)

        contribution_cd = components["CD"] * resolved_weights["CD"]
        contribution_nd = components["ND"] * resolved_weights["ND"]
        contribution_ad = components["AD"] * resolved_weights["AD"]
        contribution_md = components["MD"] * resolved_weights["MD"]

        final_pe = contribution_cd + contribution_nd + contribution_ad + contribution_md

        return PEEEAudit(
            node_id=node_id,
            body_zone=body_zone,
            cd_ms=components["CD"],
            nd_ms=components["ND"],
            ad_ms=components["AD"],
            md_ms=components["MD"],
            model=model,
            weight_cd=resolved_weights["CD"],
            weight_nd=resolved_weights["ND"],
            weight_ad=resolved_weights["AD"],
            weight_md=resolved_weights["MD"],
            contribution_cd=contribution_cd,
            contribution_nd=contribution_nd,
            contribution_ad=contribution_ad,
            contribution_md=contribution_md,
            perceived_error_ms=final_pe,
        )

    # ------------------------------------------------------------------
    # Time evolution (infrastructure for Sprint 10's live animation).
    # ------------------------------------------------------------------
    def update_timing_state(self, node, elapsed_seconds, network_condition=DEFAULT_NETWORK_CONDITION):
        """Advance a node's RAW simulated timing measurements by
        elapsed_seconds, using a seeded, per-node reproducible RNG stream.

        - Clock drift increases gradually (no resynchronization yet; that
          control logic belongs to a later sprint).
        - Network delay fluctuates via seeded stochastic jitter.
        - Actuator driver delay (AD) is treated as relatively stable.
        - Mechanical startup delay (MD) has small actuator-dependent
          variation.

        Mutates and returns the node in place. Does not itself call
        compute_error(); the coordinator's PEEE pass resolves + computes
        afterwards so the audit trail stays explicit.
        """
        rng = self._rng_for(node.node_id)

        new_clock_drift = node.clock_drift + CLOCK_DRIFT_GROWTH_MS_PER_S * elapsed_seconds
        node.clock_drift = _clamp(new_clock_drift, CLOCK_DRIFT_BOUNDS_MS)

        jitter = rng.gauss(0.0, NETWORK_JITTER_STD_MS)
        node.network_delay = _clamp(node.network_delay + jitter, NETWORK_DELAY_BOUNDS_MS)

        ad_jitter = rng.gauss(0.0, AD_JITTER_STD_MS)
        node.actuator_driver_delay = _clamp(node.actuator_driver_delay + ad_jitter, AD_BOUNDS_MS)

        md_jitter = rng.gauss(0.0, MD_JITTER_STD_MS)
        node.mechanical_startup_delay = _clamp(node.mechanical_startup_delay + md_jitter, MD_BOUNDS_MS)

        return node
