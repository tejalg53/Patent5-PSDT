"""
Sprint 10 - Time-series history storage for the Digital Twin Simulation
Engine (core/simulation_engine.py).

Pure bookkeeping only. This module never computes, classifies, or
decides anything: it only stores per-node and global samples that the
engine hands it each simulation cycle, plus a rolling human-readable
event log, so the Simulation page can render graphs/timelines/dashboards
without re-deriving state from scratch each rerun.

Two retention modes (Sprint 10 Deliverable 17):
  - Interactive Mode: bounded recent history (max_steps caps every
    series so memory stays flat during long/live interactive runs).
  - Experiment Mode: max_steps=None retains the complete run, needed for
    later (Sprint 11) experimental analysis and reproducibility checks.
"""

from typing import Dict, List, Optional

NODE_SERIES_FIELDS = (
    "step", "timestamp",
    "PT", "CD", "ND", "AD", "MD", "PE", "PSM", "NPSM", "TU",
    "current_state", "previous_state",
    "sync_interval_ms", "beacon_interval_ms", "radio_wakeup_interval_ms",
    "tx_power_pct", "trigger_offset_ms",
    "sync_event", "state_transition",
    "step_energy_j", "cumulative_energy_j", "battery_percent",
)


class SimulationHistory:
    """Bounded-or-complete time-series history for one simulation run."""

    def __init__(self, max_steps: Optional[int] = None, max_event_log: int = 1000):
        self.max_steps = max_steps
        self.max_event_log = max_event_log
        self.node_series: Dict[str, Dict[str, list]] = {}
        self.global_series: Dict[str, list] = {
            "step": [], "timestamp": [],
            "state_counts": [], "mean_pt": [], "mean_pe": [], "mean_psm": [],
            "sync_events_cum": [], "state_transitions_cum": [],
            "messages_cum": [], "energy_cum_j": [], "mean_battery_percent": [],
        }
        self.event_log: List[dict] = []

    def _node_bucket(self, node_id: str) -> Dict[str, list]:
        if node_id not in self.node_series:
            self.node_series[node_id] = {field: [] for field in NODE_SERIES_FIELDS}
        return self.node_series[node_id]

    def _trim(self, series: Dict[str, list]) -> None:
        if not self.max_steps:
            return
        for key, values in series.items():
            if len(values) > self.max_steps:
                series[key] = values[-self.max_steps:]

    def record_node_step(self, node_id: str, **kwargs) -> None:
        bucket = self._node_bucket(node_id)
        for field in NODE_SERIES_FIELDS:
            bucket[field].append(kwargs.get(field))
        self._trim(bucket)

    def record_global_step(self, **kwargs) -> None:
        for key, value in kwargs.items():
            self.global_series.setdefault(key, []).append(value)
        self._trim(self.global_series)

    def log_event(self, timestamp: float, node_id: str, message: str) -> None:
        self.event_log.append({"timestamp": timestamp, "node_id": node_id, "message": message})
        if len(self.event_log) > self.max_event_log:
            self.event_log = self.event_log[-self.max_event_log:]

    def recent_events(self, limit: int = 200) -> List[dict]:
        return list(reversed(self.event_log[-limit:]))

    def node_dataframe_dict(self, node_id: str) -> Dict[str, list]:
        return dict(self._node_bucket(node_id))

    def global_dataframe_dict(self) -> Dict[str, list]:
        return dict(self.global_series)
