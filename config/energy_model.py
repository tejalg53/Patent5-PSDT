"""
Sprint 10 - Configurable simulation energy-model parameters for the
Digital Twin Simulation Engine (core/simulation_engine.py).

These coefficients are illustrative simulation constants used to make the
digital twin's closed-loop energy/battery behavior demonstrable, exactly
as config/resource_profiles.py's ENERGY_COST_PER_ACTIVE_SECOND_BY_LEVEL
(Sprint 9) is labeled: they are NOT manufacturer hardware specifications
or measured datasheet values.

Etotal = ETX + ERX + Ewake + Esync + Eprocessing, accumulated per node.
ETX/ERX/Ewake are already estimated per simulation cycle by core/
coordinator.py's run_arac_pass() from the allocated radio wake-up
interval and transmit power (Sprint 9 Deliverable 15). This module adds
the remaining two terms that only make sense once a real time-evolving
loop exists (Sprint 10): a fixed per-resynchronization-event cost (Esync)
and a fixed per-applied-PRAP processing cost (Eprocessing).
"""

NODE_BATTERY_CAPACITY_JOULES = 500.0

SYNC_EVENT_ENERGY_J = 0.015

PRAP_APPLY_ENERGY_J = 0.004
