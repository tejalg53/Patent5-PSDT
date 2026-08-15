"""
Sprint 8 - Synchronization Classification Engine (SCE).

Classifies each node's current Normalized Perceptual Synchronization
Margin (NPSM) into one of four locked synchronization states:

RELAXED, NOMINAL, ELEVATED, IMMEDIATE

The SCE is a finite-state control machine, not a calculator: it never
recomputes PT, PE, or PSM, and it never adjusts any synchronization
parameter (sync interval, beacon interval, transmit power, etc.).
Resource adaptation is Sprint 9 (ARAC)'s responsibility, not this
engine's.

Stability against small fluctuations is enforced two ways:

- Hysteresis: each boundary gets a small "sticky" band so a value
  that has only barely crossed a threshold does not immediately
  flip the state unless it clears the boundary by more than
  HYSTERESIS_MARGIN, in the direction away from the node's
  currently committed state.
- Persistence (dwell-time): a post-hysteresis candidate state must
  be observed for STATE_PERSISTENCE_CYCLES consecutive evaluations
  before the node's committed state actually changes.

All boundary/hysteresis/persistence numbers are sourced from
config/state_boundaries.py - never hardcoded here.

Sprint 14 (Patent strengthening, Change 5): the engine now accepts
optional per-instance overrides for hysteresis_margin and
persistence_cycles. This lets the experiment layer run a controlled
"hysteresis ablation" (Change 5) - e.g. hysteresis_margin=0.0 and
persistence_cycles=1 reproduces immediate, un-damped state switching
for comparison against the default, hysteresis-protected behavior.
When no overrides are supplied the engine behaves byte-identically to
the original Sprint 8 implementation.
"""

from dataclasses import dataclass
from typing import Optional
import math

from config.state_boundaries import (
    RELAXED_MIN,
    NOMINAL_MIN,
    ELEVATED_MIN,
    HYSTERESIS_MARGIN,
    STATE_PERSISTENCE_CYCLES,
)

# The four locked synchronization states (patent architecture). Do not
# add, rename, or remove states here - see Sprint 8 Deliverable 2.
RELAXED = "RELAXED"
NOMINAL = "NOMINAL"
ELEVATED = "ELEVATED"
IMMEDIATE = "IMMEDIATE"

# Ordered lowest (least margin) -> highest (most margin).
STATE_ORDER = [IMMEDIATE, ELEVATED, NOMINAL, RELAXED]

# Sentinel used by HapticNode before its first successful classification.
UNCLASSIFIED = "Unclassified"


@dataclass(frozen=True)
class SCEResult:
    """Full, human-readable audit trail for one SCE classification.

    `status` is "OK" for a normal classification, or "INVALID_INPUT"
    when safe_classify() had to reject malformed input without raising.
    On INVALID_INPUT, current_state/transition/persistence_counter are
    simply carried over unchanged from the node's last known committed
    state - the SCE never assigns an operational state from invalid
    data (Sprint 8 Deliverable 23).
    """

    current_state: str
    previous_state: Optional[str]
    transition: bool
    persistence_counter: int
    pending_state: Optional[str]
    status: str = "OK"
    error_reason: Optional[str] = None


class SynchronizationClassificationEngine:
    """Classifies nodes into Relaxed/Nominal/Elevated/Immediate using NPSM.

    This engine performs no adaptive control. It only decides which of
    the four locked states a node currently belongs to.

    Parameters
    ----------
    hysteresis_margin : Optional[float]
        Sprint 14 (Change 5) override. When None (default), the value
        is read from config/state_boundaries.HYSTERESIS_MARGIN, which
        reproduces the original Sprint 8 behavior exactly. Pass 0.0 to
        disable hysteresis entirely for an ablation run.
    persistence_cycles : Optional[int]
        Sprint 14 (Change 5) override. When None (default), the value
        is read from config/state_boundaries.STATE_PERSISTENCE_CYCLES.
        Pass 1 to disable dwell-time persistence for an ablation run
        (a single observation is enough to commit a transition).
    """

    def __init__(self, hysteresis_margin=None, persistence_cycles=None):
        self.hysteresis_margin = (
            HYSTERESIS_MARGIN if hysteresis_margin is None else hysteresis_margin
        )
        self.persistence_cycles = (
            STATE_PERSISTENCE_CYCLES if persistence_cycles is None else persistence_cycles
        )

    def _raw_state_for(self, npsm):
        """Plain boundary classification with no hysteresis applied.
        Only used as a starting point / for previous_state-less nodes.
        """
        if npsm >= RELAXED_MIN:
            return RELAXED
        if npsm >= NOMINAL_MIN:
            return NOMINAL
        if npsm >= ELEVATED_MIN:
            return ELEVATED
        return IMMEDIATE

    def _candidate_state_for(self, npsm, previous_state):
        """Hysteresis-adjusted classification relative to previous_state.

        For each of the three boundaries (ELEVATED_MIN, NOMINAL_MIN,
        RELAXED_MIN), the effective threshold is shifted AWAY from the
        node's currently committed state: it takes a bigger move to
        leave the current state than the raw boundary would require,
        which is what prevents rapid oscillation (Deliverable 5).
        """
        if previous_state not in STATE_ORDER:
            return self._raw_state_for(npsm)

        prev_rank = STATE_ORDER.index(previous_state)
        boundaries = [ELEVATED_MIN, NOMINAL_MIN, RELAXED_MIN]

        effective = []
        for lower_rank, boundary in enumerate(boundaries):
            if prev_rank > lower_rank:
                # Previously on the upper side of this boundary - make it
                # harder to cross back down.
                effective.append(boundary - self.hysteresis_margin)
            else:
                # Previously on the lower side (or exactly at it) - make
                # it harder to cross up.
                effective.append(boundary + self.hysteresis_margin)

        eff_elevated_min, eff_nominal_min, eff_relaxed_min = effective
        if npsm >= eff_relaxed_min:
            return RELAXED
        if npsm >= eff_nominal_min:
            return NOMINAL
        if npsm >= eff_elevated_min:
            return ELEVATED
        return IMMEDIATE

    def classify(self, npsm, previous_state=None, pending_state=None,
                 persistence_counter=0):
        """Strict classification. Raises ValueError on invalid input.

        Parameters
        ----------
        npsm : float
            The node's current Normalized PSM (from PSME).
        previous_state : Optional[str]
            The node's last committed state (None / UNCLASSIFIED if this
            is the node's first evaluation).
        pending_state : Optional[str]
            The post-hysteresis candidate state observed on the previous
            evaluation, if it differed from previous_state and had not
            yet persisted long enough to commit. None if there is no
            pending candidate.
        persistence_counter : int
            How many consecutive evaluations pending_state has been
            observed for so far.

        Returns
        -------
        SCEResult
        """
        if npsm is None:
            raise ValueError("NPSM is required.")

        try:
            npsm = float(npsm)
        except (TypeError, ValueError):
            raise ValueError("NPSM must be numeric.")

        if not math.isfinite(npsm):
            raise ValueError("NPSM must be finite.")

        if previous_state is not None and previous_state not in STATE_ORDER:
            if previous_state != UNCLASSIFIED:
                raise ValueError(f"Invalid previous_state: {previous_state!r}")
            previous_state = None

        if pending_state is not None and pending_state not in STATE_ORDER:
            raise ValueError(f"Invalid pending_state: {pending_state!r}")

        candidate = self._candidate_state_for(npsm, previous_state)

        if previous_state is None:
            # First-ever classification for this node: commit immediately,
            # no dwell-time required.
            return SCEResult(
                current_state=candidate,
                previous_state=previous_state,
                transition=True,
                persistence_counter=0,
                pending_state=None,
                status="OK",
            )

        if candidate == previous_state:
            # Matches the committed state - nothing pending, no transition.
            return SCEResult(
                current_state=previous_state,
                previous_state=previous_state,
                transition=False,
                persistence_counter=0,
                pending_state=None,
                status="OK",
            )

        # candidate differs from the committed state - dwell-time applies.
        if candidate == pending_state:
            new_count = persistence_counter + 1
        else:
            new_count = 1

        if new_count >= self.persistence_cycles:
            # Candidate has persisted long enough - commit the transition.
            return SCEResult(
                current_state=candidate,
                previous_state=previous_state,
                transition=True,
                persistence_counter=0,
                pending_state=None,
                status="OK",
            )

        # Not yet persisted long enough - stay on the committed state.
        return SCEResult(
            current_state=previous_state,
            previous_state=previous_state,
            transition=False,
            persistence_counter=new_count,
            pending_state=candidate,
            status="OK",
        )

    def safe_classify(self, npsm, previous_state=None, pending_state=None,
                       persistence_counter=0):
        """Boundary-safe wrapper around classify().

        Never raises. On invalid input (None, NaN, Infinity, non-numeric,
        an unrecognized state name, etc.) it returns an SCEResult with
        status="INVALID_INPUT" whose current_state/previous_state/
        persistence_counter/pending_state simply carry over the caller's
        last known values unchanged - no operational state is assigned
        from bad data (Deliverable 23).
        """
        try:
            return self.classify(
                npsm,
                previous_state=previous_state,
                pending_state=pending_state,
                persistence_counter=persistence_counter,
            )
        except ValueError as exc:
            safe_previous = previous_state if previous_state in STATE_ORDER else UNCLASSIFIED
            return SCEResult(
                current_state=safe_previous,
                previous_state=safe_previous,
                transition=False,
                persistence_counter=persistence_counter,
                pending_state=pending_state,
                status="INVALID_INPUT",
                error_reason=str(exc),
            )
