"""
Sprint 3 - HapticNode data model.
Sprint 4 - adds the ability for a node to generate its own PSSP.

PT (Perceptual Threshold), PE (Perceived Error) and PSM (Perceptual
Synchronization Margin) are intentionally left uncomputed (None) here.
Those are produced by dedicated engines in later sprints, not faked here.
"""

from dataclasses import dataclass, field
from typing import Optional

from .packets import PSSP

# Maximum number of recent (step, PT, PE, PSM) samples retained per node.
# A bounded rolling buffer keeps memory flat for long-running simulations
# while still giving Sprint 8+ enough history for dwell-time/hysteresis
# logic and later trend visualizations.
MAX_HISTORY_LENGTH = 100

# Maximum number of recent (step, timestamp, state) samples retained per
# node's synchronization-state history (Sprint 8 SCE). Kept separate from
# MAX_HISTORY_LENGTH since it tracks classified states, not raw PT/PE/PSM.
MAX_STATE_HISTORY_LENGTH = 50


@dataclass
class HapticNode:
    # Identity / placement
    node_id: str
    body_zone: str
    actuator_type: str
    vibration_frequency: float  # Hz

    # Battery
    battery_level: float  # percent, 0-100

    # Raw timing/delay parameters
    clock_drift: float               # ms (CD)
    network_delay: float             # ms (ND)
    actuator_driver_delay: float     # ms (AD)
    mechanical_startup_delay: float  # ms (MD)

    # Sync bookkeeping
    sync_interval: float  # seconds between synchronization events

    # Uncomputed until the relevant engine (Sprint 5+) is implemented.
    perceptual_threshold: Optional[float] = None  # PT
    perceived_error: Optional[float] = None       # PE
    psm: Optional[float] = None                   # PSM
    normalized_psm: Optional[float] = None       # NPSM
    threshold_utilization_pct: Optional[float] = None  # TU
    margin_sign: Optional[str] = None             # Margin Sign
    sync_state: str = "Unclassified"        # Current State (SCE, Sprint 8)
    previous_state: Optional[str] = None          # Previous State (SCE)
    transition_flag: bool = False                 # Transition (SCE)
    persistence_counter: int = 0                  # Persistence Counter (SCE)
    pending_state: Optional[str] = None           # Internal SCE dwell-time bookkeeping

    # Telemetry counters (start at zero; updated once the time-series
    # simulation loop exists).
    packet_count: int = 0
    radio_active_time: float = 0.0  # seconds
    energy_consumed: float = 0.0    # joules

    # Rolling history of (step, timestamp, PT, PE, PSM) samples, most
    # recent last. Bounded to MAX_HISTORY_LENGTH entries. Populated by the
    # Coordinator's run_psme_pass() each cycle a valid PSM is computed.
    history: list = field(default_factory=list)

    # Rolling history of (step, timestamp, state) samples, most recent
    # last. Bounded to MAX_STATE_HISTORY_LENGTH entries. Populated by the
    # Coordinator's run_sce_pass() each cycle a state is classified.
    state_history: list = field(default_factory=list)

    def to_pssp(self, packet_id: str, simulation_timestamp: float) -> PSSP:
        """Generate this node's current Perceptual Synchronization Status Packet."""
        return PSSP(
            packet_id=packet_id,
            node_id=self.node_id,
            body_zone=self.body_zone,
            simulation_timestamp=simulation_timestamp,
            clock_drift_ms=self.clock_drift,
            network_delay_ms=self.network_delay,
            actuator_driver_delay_ms=self.actuator_driver_delay,
            mechanical_startup_delay_ms=self.mechanical_startup_delay,
            battery_percent=self.battery_level,
            current_state=self.sync_state,
        )

    def record_history_point(self, step: int, timestamp: float, pt: float, pe: float, psm: float) -> None:
        """Append one (step, timestamp, PT, PE, PSM) sample to this node's
        rolling history buffer, discarding the oldest sample once the
        buffer exceeds MAX_HISTORY_LENGTH entries.

        This is pure bookkeeping - it does not classify or interpret the
        sample. Sprint 8 uses this for dwell-time/hysteresis; Sprint 10
        for trend animation; Sprint 11 for experimental graphs.
        """
        self.history.append({
            "step": step,
            "timestamp": timestamp,
            "PT": pt,
            "PE": pe,
            "PSM": psm,
        })
        if len(self.history) > MAX_HISTORY_LENGTH:
            self.history = self.history[-MAX_HISTORY_LENGTH:]


    def record_state_history(self, step: int, timestamp: float, state: str) -> None:
        """Append one (step, timestamp, state) sample to this node's rolling
        state-history buffer, discarding the oldest sample once the buffer
        exceeds MAX_STATE_HISTORY_LENGTH entries (Sprint 8 Deliverable 8).

        Pure bookkeeping only - does not itself decide the state; that is
        the SCE's job (core/sce.py), called from the Coordinator's
        run_sce_pass().
        """
        self.state_history.append({
            "step": step,
            "timestamp": timestamp,
            "state": state,
        })
        if len(self.state_history) > MAX_STATE_HISTORY_LENGTH:
            self.state_history = self.state_history[-MAX_STATE_HISTORY_LENGTH:]
