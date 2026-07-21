"""
Sprint 8 - Configurable state-boundary values for the Synchronization
Classification Engine (SCE).

This module intentionally contains ONLY tunable numbers. core/sce.py
reads these values rather than hardcoding thresholds in engine logic,
so the simulator can be re-tuned later without touching classification
code (per Sprint 8 Deliverable 3).

All boundaries are expressed in Normalized PSM (NPSM = PSMz(t) / PTz(t)),
not raw milliseconds, because different body zones have different
absolute perceptual thresholds. NPSM is high when PE is small relative
to PT (comfortable margin) and drops below zero when PE exceeds PT.
"""

# Minimum NPSM required to be classified RELAXED (comfortably
# synchronized; large remaining margin).
RELAXED_MIN = 0.60

# Minimum NPSM required to be classified NOMINAL (normal operating
# margin).
NOMINAL_MIN = 0.30

# Minimum NPSM required to be classified ELEVATED (shrinking margin,
# still non-negative). Anything below this (negative NPSM, meaning PE
# has exceeded PT) is classified IMMEDIATE.
ELEVATED_MIN = 0.00

# Hysteresis half-band applied at each boundary. A node must clear a
# boundary by more than this margin, moving AWAY from its currently
# committed state, before that boundary counts as crossed. This is what
# stops a node from flapping back and forth when NPSM sits right at a
# boundary (Sprint 8 Deliverable 5).
HYSTERESIS_MARGIN = 0.03

# Number of consecutive evaluation cycles a post-hysteresis candidate
# state must be observed before a node's committed state actually
# changes (dwell-time / persistence, Sprint 8 Deliverable 6).
STATE_PERSISTENCE_CYCLES = 3

# Maximum number of recent (step, timestamp, state) samples retained in
# each node's rolling state_history buffer (Sprint 8 Deliverable 8).
STATE_HISTORY_LENGTH = 50
