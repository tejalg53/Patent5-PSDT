"""
Sprint 6 - Configuration / reference values for the Perceived Error
Estimation Engine (PEEE).

IMPORTANT: Every numeric value in this module is a CONFIGURABLE SIMULATION
ASSUMPTION or bound, chosen to make the PEEE residual-error model
demonstrable and auditable in the digital twin. None of these numbers are
claimed manufacturer specifications or universal physiological constants.
Before any experimental validation section is finalized, these values must
be replaced or justified using sourced evidence (component datasheets,
published network-timing measurements, etc.) per actuator type and
network condition.

Framing note (do not weaken): PEEE estimates an ESTIMATED PERCEIVED
SYNCHRONIZATION ERROR derived from RESIDUAL/DIFFERENTIAL timing
contributions affecting the temporal delivery of haptic actuation. It is
not a claim that "human perceived error is simply CD + ND + AD + MD" in
an absolute physiological sense, and it is not the same quantity as raw
end-to-end latency.
"""

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# 1. Perceived Error model selection.
# ---------------------------------------------------------------------------
PE_MODELS: Tuple[str, str] = ("additive", "weighted")
DEFAULT_PE_MODEL = "additive"

# ---------------------------------------------------------------------------
# 2. Weighted-model coefficients. Version 1.0 defaults every weight to 1.0
# (i.e. identical to the additive model) because we have no experimental
# justification yet for unequal weighting such as 0.4/0.3/0.2/0.1.
# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS: Dict[str, float] = {
    "CD": 1.0,
    "ND": 1.0,
    "AD": 1.0,
    "MD": 1.0,
}
WEIGHT_BOUNDS: Tuple[float, float] = (0.0, 5.0)

# ---------------------------------------------------------------------------
# 3. Clock Drift Contribution (CD) - configurable simulation bounds.
# CDz(t) = |clock error| relative to the coordinator/reference clock.
# Resynchronization/reset control logic belongs to a later sprint; here we
# only bound the value and, for update_timing_state(), model gradual
# growth between (not-yet-implemented) resync events.
# ---------------------------------------------------------------------------
CLOCK_DRIFT_BOUNDS_MS: Tuple[float, float] = (0.0, 50.0)
CLOCK_DRIFT_GROWTH_MS_PER_S: float = 0.01

# ---------------------------------------------------------------------------
# 4. Network Delay Contribution (ND) - residual timing uncertainty relative
# to a reference/expected delivery delay, NOT the raw measured delay.
# ---------------------------------------------------------------------------
NETWORK_REFERENCE_DELAY_MS: float = 5.0
NETWORK_RESIDUAL_BOUNDS_MS: Tuple[float, float] = (0.0, 20.0)

# Configurable simulated network conditions: an additive adjustment applied
# to the measured network delay before the residual is computed. These are
# illustrative simulation states, not measured field data.
NETWORK_CONDITION_ADJUSTMENT_MS: Dict[str, float] = {
    "Optimal": -1.0,
    "Nominal": 0.0,
    "Congested": 3.0,
    "Degraded": 6.0,
}
DEFAULT_NETWORK_CONDITION = "Nominal"

# Seeded stochastic variation applied only by update_timing_state().
NETWORK_JITTER_STD_MS: float = 1.0
NETWORK_DELAY_BOUNDS_MS: Tuple[float, float] = (0.0, 30.0)

# ---------------------------------------------------------------------------
# 5. Actuator Driver Delay (AD) - configurable per-actuator-type profile
# factor applied to the node's simulated electrical driver delay
# measurement. Distinct actuator drive electronics (LRA resonant drivers,
# ERM motor drivers, Piezo bender amplifiers) are illustratively modeled as
# having different relative electrical response delays.
# ---------------------------------------------------------------------------
ACTUATOR_AD_PROFILE_FACTOR: Dict[str, float] = {
    "LRA": 1.00,
    "ERM": 1.30,
    "Piezo": 0.70,
}
AD_BOUNDS_MS: Tuple[float, float] = (0.0, 10.0)
AD_JITTER_STD_MS: float = 0.05  # AD is treated as relatively stable over time.

# ---------------------------------------------------------------------------
# 6. Mechanical Startup Delay (MD) - configurable per-actuator-type profile
# factor. Two nodes can have perfectly synchronized clocks but still
# produce tactile outputs at different perceived times because their
# actuators reach a mechanically perceptible response at different points
# after electrical excitation (e.g. spinning-mass ERM vs. resonant LRA vs.
# piezo bender).
# ---------------------------------------------------------------------------
ACTUATOR_MD_PROFILE_FACTOR: Dict[str, float] = {
    "LRA": 1.00,
    "ERM": 1.20,
    "Piezo": 0.50,
}
MD_BOUNDS_MS: Tuple[float, float] = (0.0, 40.0)
MD_JITTER_STD_MS: float = 0.30  # small actuator-dependent variation over time.
