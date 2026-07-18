"""
Sprint 3 - Static configuration for the Distributed Wearable Node Engine.

This module intentionally contains only structural/topological constants
(zones, weights, plausible operating ranges for delay/battery/frequency
sampling). It does NOT contain any claimed psychophysical thresholds
(e.g. perceptual latency thresholds). Those values must be scientifically
sourced and justified before becoming experimental constants, and will be
introduced in a later sprint alongside the PT/PE/PSM engines.
"""

# Fixed anatomical zones for Version 1.0. Order matters: it defines the
# deterministic layout/generation order used throughout the simulation.
ZONE_ORDER = ["Fingertip", "Hand", "Forearm", "Torso", "Leg", "Foot"]

ZONE_PURPOSE = {
    "Fingertip": "High tactile sensitivity",
    "Hand": "High/moderate sensitivity",
    "Forearm": "Intermediate sensitivity",
    "Torso": "More tolerant region",
    "Leg": "Intermediate/lower sensitivity",
    "Foot": "Distinct lower-body tactile region",
}

# Relative weights used to proportionally distribute nodes across zones.
# For 30 nodes this yields: Fingertip 6, Hand 4, Forearm 4, Torso 6, Leg 6, Foot 4.
ZONE_WEIGHTS = {
    "Fingertip": 3,
    "Hand": 2,
    "Forearm": 2,
    "Torso": 3,
    "Leg": 3,
    "Foot": 2,
}

# One primary actuator type per zone (kept fixed/deterministic).
ZONE_ACTUATOR = {
    "Fingertip": "LRA",
    "Hand": "ERM",
    "Forearm": "ERM",
    "Torso": "ERM",
    "Leg": "ERM",
    "Foot": "ERM",
}

# Plausible vibration frequency ranges (Hz) by actuator type.
ACTUATOR_FREQUENCY_RANGE = {
    "LRA": (150.0, 250.0),
    "ERM": (100.0, 200.0),
}

# Plausible sampling ranges for node telemetry (not patent-derived constants).
BATTERY_RANGE = (85.0, 100.0)          # percent
CLOCK_DRIFT_RANGE = (0.5, 4.0)         # milliseconds
NETWORK_DELAY_RANGE = (2.0, 12.0)      # milliseconds
ACTUATOR_DRIVER_DELAY_RANGE = (1.0, 3.0)     # milliseconds
MECHANICAL_DELAY_RANGE = (10.0, 25.0)  # milliseconds
SYNC_INTERVAL_RANGE = (0.5, 2.0)       # seconds

# Supported node-count presets for the Digital Twin configuration panel.
NODE_COUNT_OPTIONS = [10, 20, 30, 40, 50]
