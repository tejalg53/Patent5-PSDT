"""
Sprint 3 - HapticNode data model.

This is a plain data container for a single virtual wearable haptic node.
PT (Perceptual Threshold), PE (Perceived Error) and PSM (Perceptual
Synchronization Margin) are intentionally left uncomputed (None) here.
Those are produced by dedicated engines in later sprints, not faked here.
"""

from dataclasses import dataclass
from typing import Optional


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

    # Uncomputed until the relevant engine (Sprint 4+) is implemented.
    perceptual_threshold: Optional[float] = None  # PT
    perceived_error: Optional[float] = None       # PE
    psm: Optional[float] = None                   # PSM
    sync_state: str = "Unclassified"              # State

    # Telemetry counters (start at zero; updated once the time-series
    # simulation loop exists).
    packet_count: int = 0
    radio_active_time: float = 0.0  # seconds
    energy_consumed: float = 0.0    # joules
