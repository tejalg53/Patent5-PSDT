"""
Sprint 10 - Configuration for the temporal Digital Twin Simulation Engine
(core/simulation_engine.py).

Every value in this module is a CONFIGURABLE SIMULATION PARAMETER chosen
to make Sprint 10's closed-loop, time-evolving behavior demonstrable and
auditable in the digital twin. None of these numbers are claimed
manufacturer specifications, measured field data, or physiological
constants. They follow the same "explicit configuration, not hardcoded
magic numbers" pattern already used by config/state_boundaries.py
(Sprint 8) and config/resource_profiles.py (Sprint 9).
"""

DEFAULT_DURATION_S = 300
DEFAULT_TIME_STEP_S = 1.0
DEFAULT_SEED = 42

DURATION_OPTIONS_S = [60, 120, 300, 600]
TIME_STEP_OPTIONS_S = [0.5, 1.0, 2.0, 5.0]

NETWORK_PROFILES = {
      "Stable":    {"condition": "Optimal",   "extra_jitter_std_ms": 0.3},
      "Moderate":  {"condition": "Nominal",   "extra_jitter_std_ms": 0.8},
      "Congested": {"condition": "Congested", "extra_jitter_std_ms": 2.0},
}
NETWORK_PROFILE_OPTIONS = list(NETWORK_PROFILES.keys())
DEFAULT_NETWORK_PROFILE = "Moderate"

RESYNC_RESIDUAL_MIN_MS = 0.02
RESYNC_RESIDUAL_MAX_MS = 0.25

SCENARIOS = {
      "Scenario A: Stable": {
                "description": "Stationary, stable network, low disturbance.",
                "timeline": [
                              (0.0, "Stationary", "Stable", "Low disturbance"),
                ],
      },
      "Scenario B: Moderate": {
                "description": "Walking, moderate network variation, normal disturbance.",
                "timeline": [
                              (0.0, "Walking", "Moderate", "Normal"),
                ],
      },
      "Scenario C: Dynamic/Challenging": {
                "description": (
                              "Stationary to Walking to Running; Stable to Moderate to "
                              "Congested network; rising disturbance."
                ),
                "timeline": [
                              (0.0, "Stationary", "Stable", "Normal"),
                              (1 / 3, "Walking", "Moderate", "Normal"),
                              (2 / 3, "Running", "Congested", "High vibration/noise"),
                ],
      },
}
SCENARIO_OPTIONS = list(SCENARIOS.keys())
DEFAULT_SCENARIO = "Scenario B: Moderate"

INTERACTIVE_HISTORY_MAX_STEPS = 300
EXPERIMENT_HISTORY_MAX_STEPS = None

DISTURBANCE_NETWORK_JITTER_SPIKE_MS = 15.0
DISTURBANCE_CLOCK_DRIFT_SPIKE_MS = 8.0
DISTURBANCE_ENVIRONMENT_STATE = "High vibration/noise"
