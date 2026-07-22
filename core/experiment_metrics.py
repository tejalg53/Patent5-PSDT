"""
Sprint 11: Experimental metrics for the controlled comparison between
the Uniform Baseline and the PSM-Adaptive Proposed method
(core/experiment_engine.py).

Pure computation over an already-finished DigitalTwinSimulationEngine
run's history/status: this module never runs a simulation itself and
never recomputes PT/PE/PSM/state (Sprint 5-9's job) or resource
allocation (ARAC, Sprint 9). It only aggregates and compares what the
engine already produced, per Sprint 11 Deliverables 5, 6, 20 and 26.
"""

import math
import random as _random
import statistics
from typing import List, Optional

from config.baseline_policies import VIOLATION_RATE_TOLERANCE_PP


def _percentile(sorted_values, pct):
    if not sorted_values:
        return None
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def compute_run_metrics(engine) -> dict:
    """Aggregate one finished engine run's history into the primary and
    secondary Sprint 11 metrics (Deliverables 5-6)."""
    status = engine.status()
    registry = engine.coordinator.registry

    psm_observations: List[float] = []
    pe_observations: List[float] = []
    pt_observations: List[float] = []
    violation_count = 0
    nodes_with_violation = set()

    for node_id, series in engine.history.node_series.items():
        for psm in series["PSM"]:
            if psm is None:
                continue
            psm_observations.append(psm)
            if psm < 0:
                violation_count += 1
                nodes_with_violation.add(node_id)
        for pe in series["PE"]:
            if pe is not None:
                pe_observations.append(pe)
        for pt in series["PT"]:
            if pt is not None:
                pt_observations.append(pt)

    total_observations = len(psm_observations)
    violation_rate_pct = (
        (violation_count / total_observations) * 100.0 if total_observations else 0.0
    )
    sorted_psm = sorted(psm_observations)

    total_radio_active_time = sum(n.radio_active_time for n in registry.values())
    total_energy = sum(n.energy_consumed for n in registry.values())
    mean_battery_remaining = (
        sum(n.battery_level for n in registry.values()) / len(registry) if registry else None
    )
    sync_interval_samples = [
        v for s in engine.history.node_series.values() for v in s["sync_interval_ms"] if v is not None
    ]
    tx_power_samples = [
        v for s in engine.history.node_series.values() for v in s["tx_power_pct"] if v is not None
    ]

    beacon_count_est = 0.0
    wakeup_count_est = 0.0
    dt = engine.dt
    for series in engine.history.node_series.values():
        for b in series["beacon_interval_ms"]:
            if b:
                beacon_count_est += dt / (b / 1000.0)
        for w in series["radio_wakeup_interval_ms"]:
            if w:
                wakeup_count_est += dt / (w / 1000.0)

    return {
        "experiment_id": getattr(engine, "experiment_id", None),
        "model_version": getattr(engine, "model_version", None),
        "control_mode": engine.control_mode,
        "baseline_policy": getattr(engine, "baseline_policy", None),
        "seed": engine.seed,
        "num_nodes": engine.num_nodes,
        "scenario": engine.scenario_name,
        "duration_s": engine.duration_s,
        "sync_messages": status["sync_events"],
        "radio_active_time_s": total_radio_active_time,
        "radio_active_time_mean_per_node_s": (
            total_radio_active_time / len(registry) if registry else 0.0
        ),
        "estimated_energy_j": total_energy,
        "violation_events": violation_count,
        "violation_time_steps": total_observations,
        "affected_nodes": len(nodes_with_violation),
        "violation_rate_pct": violation_rate_pct,
        "mean_psm": statistics.fmean(psm_observations) if psm_observations else None,
        "median_psm": statistics.median(psm_observations) if psm_observations else None,
        "min_psm": min(psm_observations) if psm_observations else None,
        "p5_psm": _percentile(sorted_psm, 5),
        "negative_psm_frequency_pct": violation_rate_pct,
        "state_transitions": status["state_transitions"],
        "state_counts": status["state_counts"],
        "beacon_count_estimated": beacon_count_est,
        "pssp_count": engine.coordinator.get_packet_counts()["generated"],
        "prap_count": engine.coordinator.prap_generated,
        "radio_wakeup_events_estimated": wakeup_count_est,
        "mean_sync_interval_ms": (
            statistics.fmean(sync_interval_samples) if sync_interval_samples else None
        ),
        "mean_tx_power_pct": statistics.fmean(tx_power_samples) if tx_power_samples else None,
        "mean_battery_percent": mean_battery_remaining,
        "max_pe": max(pe_observations) if pe_observations else None,
        "mean_pe": statistics.fmean(pe_observations) if pe_observations else None,
        "mean_pt": statistics.fmean(pt_observations) if pt_observations else None,
        "control_action_count": status["state_transitions"],
        "invariant_violations": status["invariant_violations"],
    }


def compare_runs(baseline: dict, proposed: dict) -> dict:
    """Sprint 11 Deliverable 13/14: pairwise comparison of one baseline
    run's metrics against one proposed run's metrics."""

    def _reduction_pct(b, p):
        if b in (None, 0):
            return None
        return (b - p) / b * 100.0

    return {
        "sync_messages": {
            "baseline": baseline["sync_messages"], "proposed": proposed["sync_messages"],
            "reduction_pct": _reduction_pct(baseline["sync_messages"], proposed["sync_messages"]),
        },
        "radio_active_time_s": {
            "baseline": baseline["radio_active_time_s"], "proposed": proposed["radio_active_time_s"],
            "reduction_pct": _reduction_pct(
                baseline["radio_active_time_s"], proposed["radio_active_time_s"]
            ),
        },
        "estimated_energy_j": {
            "baseline": baseline["estimated_energy_j"], "proposed": proposed["estimated_energy_j"],
            "reduction_pct": _reduction_pct(
                baseline["estimated_energy_j"], proposed["estimated_energy_j"]
            ),
        },
        "violation_rate_pct": {
            "baseline": baseline["violation_rate_pct"], "proposed": proposed["violation_rate_pct"],
            "difference_pp": proposed["violation_rate_pct"] - baseline["violation_rate_pct"],
        },
        "mean_psm": {
            "baseline": baseline["mean_psm"], "proposed": proposed["mean_psm"],
            "difference": (
                proposed["mean_psm"] - baseline["mean_psm"]
                if baseline["mean_psm"] is not None and proposed["mean_psm"] is not None
                else None
            ),
        },
        "min_psm": {
            "baseline": baseline["min_psm"], "proposed": proposed["min_psm"],
            "difference": (
                proposed["min_psm"] - baseline["min_psm"]
                if baseline["min_psm"] is not None and proposed["min_psm"] is not None
                else None
            ),
        },
        "state_transitions": {
            "baseline": baseline["state_transitions"], "proposed": proposed["state_transitions"],
        },
        "mean_sync_interval_ms": {
            "baseline": baseline["mean_sync_interval_ms"], "proposed": proposed["mean_sync_interval_ms"],
        },
    }


def aggregate_metric(values: List[Optional[float]]) -> dict:
    values = [v for v in values if v is not None]
    if not values:
        return {"mean": None, "median": None, "stdev": None, "min": None, "max": None, "n": 0}
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "n": len(values),
    }


def bootstrap_ci(values: List[Optional[float]], n_boot: int = 1000, alpha: float = 0.05,
                  seed: int = 0) -> Optional[tuple]:
    """Simple percentile bootstrap confidence interval for the mean of
    values (Sprint 11 Deliverable 20: a simple bootstrap confidence
    interval is fine if implemented correctly and documented). Returns
    (lower, upper) or None if fewer than 2 values are available."""
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return None
    rng = _random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.fmean(sample))
    means.sort()
    lo = _percentile(means, (alpha / 2.0) * 100.0)
    hi = _percentile(means, (1.0 - alpha / 2.0) * 100.0)
    return (lo, hi)


def paired_seed_differences(baseline_runs: List[dict], proposed_runs: List[dict], metric: str) -> dict:
    """Sprint 11 Deliverable 20: per-seed paired differences for one
    metric across multiple seeds, plus the mean paired difference and a
    bootstrap CI on that mean difference."""
    diffs = []
    for b, p in zip(baseline_runs, proposed_runs):
        bv, pv = b.get(metric), p.get(metric)
        if bv is not None and pv is not None:
            diffs.append(pv - bv)
    ci = bootstrap_ci(diffs)
    return {
        "per_seed_diff": diffs,
        "mean_diff": statistics.fmean(diffs) if diffs else None,
        "ci_95": ci,
    }


def sanity_check(baseline: dict, proposed: dict) -> List[str]:
    """Sprint 11 Deliverable 26: flag suspicious outcomes automatically.
    Never modifies parameters to fix a bad outcome; only reports."""
    warnings = []

    if (
        baseline.get("mean_sync_interval_ms") is not None
        and proposed.get("mean_sync_interval_ms") is not None
        and abs(baseline["mean_sync_interval_ms"] - proposed["mean_sync_interval_ms"]) < 1e-6
    ):
        warnings.append(
            "WARNING: Baseline and Proposed have identical mean synchronization interval."
        )

    if proposed.get("state_transitions", 0) == 0:
        warnings.append("WARNING: Zero state transitions recorded for the Proposed run.")

    if proposed.get("violation_rate_pct") == 100.0:
        warnings.append("WARNING: 100% threshold violations in the Proposed run.")

    if proposed.get("violation_rate_pct") == 0.0:
        warnings.append(
            "NOTE: 0% violations in the Proposed run under this scenario, inspect assumptions "
            "(is the scenario actually challenging enough to be informative?)."
        )

    if (
        proposed.get("estimated_energy_j") is not None
        and baseline.get("estimated_energy_j") is not None
        and proposed["estimated_energy_j"] >= baseline["estimated_energy_j"]
        and proposed.get("violation_rate_pct", 0.0) > baseline.get("violation_rate_pct", 0.0)
    ):
        warnings.append(
            "WARNING: Proposed method used more energy AND had a worse violation rate than "
            "Baseline for this run. Reporting honestly, investigate the model rather than "
            "hiding this result."
        )

    return warnings


def evaluate_success_criterion(baseline: dict, proposed: dict,
                                tolerance_pp: float = VIOLATION_RATE_TOLERANCE_PP) -> dict:
    """Sprint 11 Deliverable 21: apply the pre-registered technical
    success criterion. Defined and documented before results are
    interpreted; the tolerance is never adjusted after the fact."""
    energy_reduced = (
        proposed.get("estimated_energy_j", 0.0) < baseline.get("estimated_energy_j", 0.0)
    )
    messages_reduced = proposed.get("sync_messages", 0) < baseline.get("sync_messages", 0)
    violation_diff_pp = proposed.get("violation_rate_pct", 0.0) - baseline.get("violation_rate_pct", 0.0)
    within_tolerance = violation_diff_pp <= tolerance_pp

    success = (energy_reduced or messages_reduced) and within_tolerance
    return {
        "success": success,
        "energy_reduced": energy_reduced,
        "messages_reduced": messages_reduced,
        "violation_diff_pp": violation_diff_pp,
        "tolerance_pp": tolerance_pp,
        "within_tolerance": within_tolerance,
    }
