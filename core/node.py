"""
Sprint 3 - HapticNode data model.
Sprint 4 - adds the ability for a node to generate its own PSSP.

PT (Perceptual Threshold), PE (Perceived Error) and PSM (Perceptual
Synchronization Margin) are intentionally left uncomputed (None) here.
Those are produced by dedicated engines in later sprints, not faked here.
"""

from dataclasses import dataclass
from typing import Optional

from .packets import PSSP


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
    sync_state: str = "Unclassified"              # State

    # Telemetry counters (start at zero; updated once the time-series
    # simulation loop exists).
    packet_count: int = 0
    radio_active_time: float = 0.0  # seconds
    energy_consumed: float = 0.0    # joules

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
