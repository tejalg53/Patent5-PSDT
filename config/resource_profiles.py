"""
Sprint 9 - Configurable resource-allocation profiles for the Adaptive
Resource Allocation Controller (ARAC).

This module intentionally contains ONLY tunable numbers/labels. core/arac.py
reads these values rather than hardcoding resource-allocation decisions in
engine logic, mirroring Sprint 8 Deliverable 3's config/state_boundaries.py
pattern so the simulator can be re-tuned later without touching controller
code.

Each locked synchronization state (see core/sce.py STATE_ORDER) maps to a
resource profile: a synchronization interval, a beacon interval, a radio
wake-up interval, and a transmit power level. States with less perceptual
margin (ELEVATED, IMMEDIATE) get shorter intervals and higher power so
synchronization quality is protected; states with a comfortable margin
(RELAXED, NOMINAL) get longer intervals and lower power to reduce
communication overhead and energy consumption (Sprint 9 Deliverables 3-7).

All values are illustrative simulation constants used to demonstrate the
adaptive control behavior described in the patent - they are not derived
from a specific radio's datasheet.
"""

# Synchronization interval, in milliseconds, between synchronization
# events. Shorter for less-comfortable states (Sprint 9 Deliverable 3).
SYNC_INTERVAL_MS_BY_STATE = {
    "RELAXED": 2000.0,
    "NOMINAL": 1000.0,
    "ELEVATED": 500.0,
    "IMMEDIATE": 200.0,
}

# Beacon interval in milliseconds (time between synchronization beacons).
# A lower interval means a higher beacon frequency (Sprint 9 Deliverable 4).
BEACON_INTERVAL_MS_BY_STATE = {
    "RELAXED": 100.0,
    "NOMINAL": 60.0,
    "ELEVATED": 40.0,
    "IMMEDIATE": 20.0,
}

# Radio wake-up interval in milliseconds - how often the radio wakes to
# check for synchronization traffic when otherwise idle (Sprint 9
# Deliverable 5). A longer interval means more time asleep and more
# energy saved.
RADIO_WAKEUP_INTERVAL_MS_BY_STATE = {
    "RELAXED": 500.0,
    "NOMINAL": 250.0,
    "ELEVATED": 100.0,
    "IMMEDIATE": 20.0,
}

# Transmit power label plus its normalized (0-100%) numeric value used for
# analytics/energy estimation (Sprint 9 Deliverable 7).
TRANSMIT_POWER_LEVEL_BY_STATE = {
    "RELAXED": "Low",
    "NOMINAL": "Medium",
    "ELEVATED": "High",
    "IMMEDIATE": "Maximum",
}
TRANSMIT_POWER_PCT_BY_STATE = {
    "RELAXED": 20.0,
    "NOMINAL": 50.0,
    "ELEVATED": 80.0,
    "IMMEDIATE": 100.0,
}

# Fixed, pre-ARAC baseline resource profile. Used by the Analytics page's
# "Before ARAC / After ARAC" comparison (Sprint 9 Deliverable 14) and as
# the documented default described below.
FIXED_BASELINE_SYNC_INTERVAL_MS = 1000.0
FIXED_BASELINE_BEACON_INTERVAL_MS = 60.0
FIXED_BASELINE_RADIO_WAKEUP_INTERVAL_MS = 250.0
FIXED_BASELINE_TRANSMIT_POWER_LEVEL = "Medium"
FIXED_BASELINE_TRANSMIT_POWER_PCT = 50.0

# Documented defaults applied when ARAC must safely fall back rather than
# produce an undefined allocation (Sprint 9 Deliverable 23), and there is
# no previous allocation on the node to retain instead. Deliberately the
# same conservative NOMINAL profile used elsewhere in the simulator.
DEFAULT_SYNC_INTERVAL_MS = SYNC_INTERVAL_MS_BY_STATE["NOMINAL"]
DEFAULT_BEACON_INTERVAL_MS = BEACON_INTERVAL_MS_BY_STATE["NOMINAL"]
DEFAULT_RADIO_WAKEUP_INTERVAL_MS = RADIO_WAKEUP_INTERVAL_MS_BY_STATE["NOMINAL"]
DEFAULT_TRANSMIT_POWER_LEVEL = TRANSMIT_POWER_LEVEL_BY_STATE["NOMINAL"]
DEFAULT_TRANSMIT_POWER_PCT = TRANSMIT_POWER_PCT_BY_STATE["NOMINAL"]
DEFAULT_TRIGGER_OFFSET_MS = 0.0

# Per-body-zone scaling factor applied to the state-driven synchronization
# interval, so anatomically differentiated zones receive differentiated
# resource allocation even at the same synchronization state (Sprint 9
# Deliverables 14/17). Values below 1.0 tighten (shorten) the interval for
# more tactile-sensitive zones; values above 1.0 relax it for more
# tolerant zones. Illustrative simulation constants only.
ZONE_SYNC_SCALE = {
    "Fingertip": 0.60,
    "Hand": 0.75,
    "Forearm": 0.90,
    "Torso": 1.30,
    "Leg": 1.10,
    "Foot": 1.20,
}
DEFAULT_ZONE_SYNC_SCALE = 1.0

# Estimated relative energy cost, in arbitrary joules per second of radio
# radio-active time, at each transmit-power level. Used only to produce
# the simulator's illustrative energy-estimation analytics (Sprint 9
# Deliverable 15). These are estimated values derived from the simulation
# model, not direct hardware measurements.
ENERGY_COST_PER_ACTIVE_SECOND_BY_LEVEL = {
    "Low": 0.05,
    "Medium": 0.10,
    "High": 0.18,
    "Maximum": 0.25,
}

# Fixed assumed radio listen duration, in seconds, consumed each time the
# radio wakes up to check for traffic. Used with the wake-up interval to
# estimate radio_active_time per simulation cycle (Sprint 9 Deliverable 15).
RADIO_WAKE_DURATION_S = 0.004
