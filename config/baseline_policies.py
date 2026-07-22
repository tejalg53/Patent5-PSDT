"""
Sprint 11: Baseline (uniform, non-adaptive) synchronization policies for
the controlled experimental comparison (core/experiment_engine.py).

These are CONFIGURABLE SIMULATION PARAMETERS documenting the fixed,
non-adaptive resource policy every node uses under "Baseline A: Uniform
Synchronization" (Sprint 11 Deliverable 3). They intentionally reuse the
already-committed Sprint 9 FIXED_BASELINE_* constants (config/
resource_profiles.py) as the primary policy, since that is the exact
fixed profile the patent's Sprint 9 "Before ARAC" comparison already
used: there is one single source of truth for what a uniform node gets,
not two competing definitions.

A second, stricter fixed policy (Uniform-Conservative) is included so the
comparison is not run against only one hand-picked uniform configuration
(Sprint 11 Deliverable 3, "fairness rule").

Sprint 11 Deliverable 1 also requires freezing the Sprint 10 temporal
closed-loop model before experimentation begins. MODEL_VERSION below is
that frozen tag; equations, thresholds, state boundaries, and energy
coefficients are NOT modified as part of Sprint 11 unless a genuine bug
is found, in which case this version string must be incremented and all
experiments rerun (Deliverable 1).
"""

from config.resource_profiles import (
    FIXED_BASELINE_SYNC_INTERVAL_MS,
    FIXED_BASELINE_BEACON_INTERVAL_MS,
    FIXED_BASELINE_RADIO_WAKEUP_INTERVAL_MS,
    FIXED_BASELINE_TRANSMIT_POWER_LEVEL,
    FIXED_BASELINE_TRANSMIT_POWER_PCT,
)

MODEL_VERSION = "PSDT v1.0-sim (Temporal Closed-Loop Model, frozen for Sprint 11)"

UNIFORM_POLICIES = {
    "Uniform-Moderate": {
        "description": "Sprint 9 fixed pre-ARAC baseline profile (NOMINAL-equivalent fixed settings).",
        "sync_interval_ms": FIXED_BASELINE_SYNC_INTERVAL_MS,
        "beacon_interval_ms": FIXED_BASELINE_BEACON_INTERVAL_MS,
        "radio_wakeup_interval_ms": FIXED_BASELINE_RADIO_WAKEUP_INTERVAL_MS,
        "transmit_power_level": FIXED_BASELINE_TRANSMIT_POWER_LEVEL,
        "transmit_power_pct": FIXED_BASELINE_TRANSMIT_POWER_PCT,
    },
    "Uniform-Conservative": {
        "description": "A stricter fixed policy (ELEVATED-equivalent fixed settings) applied uniformly to every node, regardless of state.",
        "sync_interval_ms": 500.0,
        "beacon_interval_ms": 40.0,
        "radio_wakeup_interval_ms": 100.0,
        "transmit_power_level": "High",
        "transmit_power_pct": 80.0,
    },
}
UNIFORM_POLICY_OPTIONS = list(UNIFORM_POLICIES.keys())
DEFAULT_UNIFORM_POLICY = "Uniform-Moderate"

# Sprint 11 Deliverable 21: technical-success criterion, defined BEFORE
# looking at results. The proposed PSM-adaptive method is considered
# successful if it reduces synchronization messages and/or estimated
# communication energy relative to the uniform baseline, while its
# perceptual-threshold violation rate stays within this tolerance
# (percentage points) of the baseline's violation rate.
VIOLATION_RATE_TOLERANCE_PP = 5.0

# Sprint 11 Deliverable 8: default disturbance-injection window (as a
# fraction of total duration) used by the controlled disturbance
# experiment, and the persistence window (consecutive steps) required to
# declare "recovered" (Deliverable 8's recovery criterion, applied
# identically to both methods).
DISTURBANCE_START_FRACTION = 1.0 / 3.0
DISTURBANCE_END_FRACTION = 0.5
RECOVERY_PERSISTENCE_STEPS = 5

# Sprint 11 Deliverable 9/27: default seed list and reduced experiment
# matrix sizes used by the interactive dashboard. The full matrix
# described in Deliverable 27 (3 scenarios x 5 node counts x 10 seeds x
# 2 strategies = 300 runs) is supported by the engine, but the dashboard
# defaults to a smaller matrix so it completes in an interactive
# Streamlit session; users may raise these controls toward the full
# matrix (Deliverable 27 explicitly allows a documented reduced matrix
# if runtime is too high).
DEFAULT_SEED_LIST = [42, 43, 44, 45, 46]
FULL_SEED_LIST = list(range(42, 52))
DEFAULT_SCALABILITY_NODE_COUNTS = [10, 20, 30, 40, 50]
DEFAULT_SCALABILITY_SEED_COUNT = 3
