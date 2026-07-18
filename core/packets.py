"""
Sprint 4 - Patent packet structures.

PSSP (Perceptual Synchronization Status Packet): sent from a wearable node
to the Central Synchronization Coordinator, describing its current raw
timing/battery/state.

PRAP (Perceptual Resource Allocation Packet): sent from the coordinator
back to a node. This sprint only defines the STRUCTURE. Values are left
as None / a clearly labeled baseline - ARAC (Sprint 9) is responsible for
populating these with real PSM-driven adaptive decisions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PSSP:
    """Perceptual Synchronization Status Packet."""

    packet_id: str
    node_id: str
    body_zone: str
    simulation_timestamp: float

    clock_drift_ms: float
    network_delay_ms: float
    actuator_driver_delay_ms: float
    mechanical_startup_delay_ms: float

    battery_percent: float
    current_state: str


@dataclass
class PRAP:
    """
    Perceptual Resource Allocation Packet (structural skeleton only).

    is_baseline=True indicates these values are NOT derived from PSM/ARAC
    logic yet - they are placeholders so the packet shape exists ahead of
    Sprint 9.
    """

    packet_id: str
    target_node_id: str
    body_zone: str
    simulation_timestamp: float

    target_state: Optional[str] = None
    sync_interval_ms: Optional[float] = None
    beacon_interval_ms: Optional[float] = None
    radio_wakeup_interval_ms: Optional[float] = None
    transmit_power_level: Optional[str] = None
    trigger_timing_offset_ms: Optional[float] = None
    is_baseline: bool = True
