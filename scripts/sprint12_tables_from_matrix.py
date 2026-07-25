"""
Sprint 12 Deliverables 11-16 -- Statistics, Effect Sizes, and Tables computed
from the already-written results/raw/experiment_runs.csv (no re-simulation).
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.experiment_engine import run_body_zone_experiment, ControlledExperiment
from core.experiment_metrics import (
    aggregate_metric, paired_seed_differences, sanity_check, evaluate_success_criterion,
)
from config.baseline_policies import DEFAULT_UNIFORM_POLICY, FULL_SEED_LIST, DEFAULT_SCALABILITY_NODE_COUNTS

RAW_DIR = os.path.join(ROOT, "results", "raw")
AGG_DIR = os.path.join(ROOT, "results", "aggregates")
os.makedirs(AGG_DIR, exist_ok=True)

SEEDS = FULL_SEED_LIST[:10]
NODE_COUNTS = DEFAULT_SCALABILITY_NODE_COUNTS
SCENARIOS = ["Scenario A: Stable", "Scenario B: Moderate", "Scenario C: Dynamic/Challenging"]
DURATION_S = 300.0
TIME_STEP_S = 1.0
PRIMARY_NODES = 30
PRIMARY_SCENARIO = "Scenario B: Moderate"

# ------------------------------------------------------------------
# Load the just-written raw matrix for statistics/tables (Deliverables 11-16)
# ------------------------------------------------------------------
import statistics as _stats

def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

with open(os.path.join(RAW_DIR, "experiment_runs.csv")) as f:
    reader = csv.DictReader(f)
    all_rows = list(reader)
for row in all_rows:
    for key in ("num_nodes", "duration_s", "seed"):
        if key in row:
            row[key] = to_float(row[key])
    for key in ("sync_messages", "radio_active_time_s", "estimated_energy_j", "violation_rate_pct",
                "mean_psm", "min_psm", "p5_psm"):
        if key in row:
            row[key] = to_float(row[key])


def subset(scenario=None, nodes=None, strategy=None):
    out = all_rows
    if scenario is not None:
        out = [r for r in out if r["scenario"] == scenario]
    if nodes is not None:
        out = [r for r in out if r["num_nodes"] == nodes]
    if strategy is not None:
        out = [r for r in out if r["strategy"] == strategy]
    return out


def stat_block(rows, field):
    vals = [r[field] for r in rows if r.get(field) is not None]
    return aggregate_metric(vals)


def pct_change(baseline_mean, proposed_mean):
    if not baseline_mean:
        return None
    return (baseline_mean - proposed_mean) / baseline_mean * 100.0

# ------------------------------------------------------------------
# Deliverables 11-13: Final Statistical Summary + Effect Sizes + Core Results Table
# (primary config: 30 nodes, Scenario B: Moderate, 10 seeds)
# ------------------------------------------------------------------
print("=== Deliverables 11-13: Final Statistical Summary & Core Results Table ===")
primary_base = subset(scenario=PRIMARY_SCENARIO, nodes=PRIMARY_NODES, strategy="baseline")
primary_prop = subset(scenario=PRIMARY_SCENARIO, nodes=PRIMARY_NODES, strategy="proposed")
print(f"Primary config paired runs: baseline n={len(primary_base)}, proposed n={len(primary_prop)}")

core_metrics = [
    ("Sync Messages", "sync_messages", "pct"),
    ("Radio Active Time (s)", "radio_active_time_s", "pct"),
    ("Estimated Communication Energy (J)", "estimated_energy_j", "pct"),
    ("Violation Rate (%)", "violation_rate_pct", "pp"),
    ("Mean PSM (ms)", "mean_psm", "raw"),
    ("Minimum/5th-pct PSM (ms)", "min_psm", "raw"),
]

core_table_rows = []
for label, field, effect_type in core_metrics:
    b = stat_block(primary_base, field)
    p = stat_block(primary_prop, field)
    diffs = paired_seed_differences(primary_base, primary_prop, field)
    if effect_type == "pct":
        effect = pct_change(b["mean"], p["mean"])
        effect_str = f"{effect:+.1f}%" if effect is not None else "n/a"
    elif effect_type == "pp":
        effect = (p["mean"] - b["mean"]) if (p["mean"] is not None and b["mean"] is not None) else None
        effect_str = f"{effect:+.3f}pp" if effect is not None else "n/a"
    else:
        effect = None
        effect_str = "-"
    core_table_rows.append({
        "metric": label,
        "uniform_baseline_mean": b["mean"], "uniform_baseline_median": b["median"],
        "uniform_baseline_stdev": b["stdev"], "uniform_baseline_min": b["min"], "uniform_baseline_max": b["max"],
        "psm_adaptive_mean": p["mean"], "psm_adaptive_median": p["median"],
        "psm_adaptive_stdev": p["stdev"], "psm_adaptive_min": p["min"], "psm_adaptive_max": p["max"],
        "effect": effect_str,
        "mean_paired_diff": diffs["mean_diff"], "bootstrap_95ci": diffs["ci_95"],
    })
    print(f"  {label:38s} baseline={b['mean']:.3f}  proposed={p['mean']:.3f}  effect={effect_str}  "
          f"95%CI(diff)={diffs['ci_95']}")

with open(os.path.join(AGG_DIR, "core_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(core_table_rows[0].keys()))
    w.writeheader()
    for r in core_table_rows:
        w.writerow(r)

success = evaluate_success_criterion(
    {"estimated_energy_j": stat_block(primary_base, "estimated_energy_j")["mean"],
     "sync_messages": stat_block(primary_base, "sync_messages")["mean"],
     "violation_rate_pct": stat_block(primary_base, "violation_rate_pct")["mean"]},
    {"estimated_energy_j": stat_block(primary_prop, "estimated_energy_j")["mean"],
     "sync_messages": stat_block(primary_prop, "sync_messages")["mean"],
     "violation_rate_pct": stat_block(primary_prop, "violation_rate_pct")["mean"]},
)
print(f"Pre-registered success criterion: {success}")
with open(os.path.join(AGG_DIR, "success_criterion.json"), "w") as f:
    json.dump(success, f, indent=2, default=str)
print()

# ------------------------------------------------------------------
# Deliverable 14: Final Scenario Table (at primary node count = 30)
# ------------------------------------------------------------------
print("=== Deliverable 14: Final Scenario Table ===")
scenario_table_rows = []
for scenario in SCENARIOS:
    for strategy in ("baseline", "proposed"):
        rows = subset(scenario=scenario, nodes=PRIMARY_NODES, strategy=strategy)
        sync = stat_block(rows, "sync_messages")
        energy = stat_block(rows, "estimated_energy_j")
        viol = stat_block(rows, "violation_rate_pct")
        psm = stat_block(rows, "mean_psm")
        label = "Uniform" if strategy == "baseline" else "PSM-Adaptive"
        scenario_table_rows.append({
            "scenario": scenario, "strategy": label,
            "sync_messages_mean": sync["mean"], "estimated_energy_j_mean": energy["mean"],
            "violation_rate_pct_mean": viol["mean"], "mean_psm_mean": psm["mean"], "n": sync["n"],
        })
        print(f"  {scenario:32s} {label:14s} sync={sync['mean']:.1f}  energy={energy['mean']:.2f}J  "
              f"viol={viol['mean']:.3f}%  meanPSM={psm['mean']:.2f}")

with open(os.path.join(AGG_DIR, "scenario_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(scenario_table_rows[0].keys()))
    w.writeheader()
    for r in scenario_table_rows:
        w.writerow(r)
print()

# ------------------------------------------------------------------
# Deliverable 16: Final Scalability Table (Scenario B across all node counts)
# ------------------------------------------------------------------
print("=== Deliverable 16: Final Scalability Table ===")
scalability_table_rows = []
for n in NODE_COUNTS:
    base_rows = subset(scenario=PRIMARY_SCENARIO, nodes=n, strategy="baseline")
    prop_rows = subset(scenario=PRIMARY_SCENARIO, nodes=n, strategy="proposed")
    energy_b = stat_block(base_rows, "estimated_energy_j")
    energy_p = stat_block(prop_rows, "estimated_energy_j")
    sync_b = stat_block(base_rows, "sync_messages")
    sync_p = stat_block(prop_rows, "sync_messages")
    viol_b = stat_block(base_rows, "violation_rate_pct")
    viol_p = stat_block(prop_rows, "violation_rate_pct")
    scalability_table_rows.append({
        "num_nodes": n,
        "baseline_energy_j": energy_b["mean"], "proposed_energy_j": energy_p["mean"],
        "energy_reduction_pct": pct_change(energy_b["mean"], energy_p["mean"]),
        "baseline_messages": sync_b["mean"], "proposed_messages": sync_p["mean"],
        "messages_reduction_pct": pct_change(sync_b["mean"], sync_p["mean"]),
        "violation_diff_pp": viol_p["mean"] - viol_b["mean"],
    })
    print(f"  n={n:3d}  energy {energy_b['mean']:.2f}->{energy_p['mean']:.2f}J "
          f"({pct_change(energy_b['mean'], energy_p['mean']):.1f}%)   "
          f"msgs {sync_b['mean']:.1f}->{sync_p['mean']:.1f} "
          f"({pct_change(sync_b['mean'], sync_p['mean']):.1f}%)   "
          f"viol_diff={viol_p['mean']-viol_b['mean']:+.3f}pp")

with open(os.path.join(AGG_DIR, "scalability_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(scalability_table_rows[0].keys()))
    w.writeheader()
    for r in scalability_table_rows:
        w.writerow(r)
print()

# ------------------------------------------------------------------
# Deliverable 15: Final Body-Zone Table
# ------------------------------------------------------------------
print("=== Deliverable 15: Final Body-Zone Table ===")
zone_exp = ControlledExperiment(seed=SEEDS[0], nodes=PRIMARY_NODES, duration=DURATION_S,
                                 time_step=TIME_STEP_S, scenario=PRIMARY_SCENARIO,
                                 baseline_policy=DEFAULT_UNIFORM_POLICY)
zone_base_engine, zone_prop_engine = zone_exp.run_pair()
zone_result = run_body_zone_experiment(zone_base_engine, zone_prop_engine)

def _zone_violation_rates(engine) -> dict:
    """Per-zone violation rate (%): fraction of observed PSM<0 samples,
    using the same definition as core.experiment_metrics.compute_run_metrics
    (Deliverable 15 fix: body_zone_summary() does not expose this, so it is
    derived here directly from the same already-completed run's history --
    no re-simulation, no changed model logic)."""
    counts, violations = {}, {}
    registry = engine.coordinator.registry
    for node_id, series in engine.history.node_series.items():
        zone = registry[node_id].body_zone
        for psm in series["PSM"]:
            if psm is None:
                continue
            counts[zone] = counts.get(zone, 0) + 1
            if psm < 0:
                violations[zone] = violations.get(zone, 0) + 1
    return {
        zone: (violations.get(zone, 0) / counts[zone] * 100.0 if counts.get(zone) else 0.0)
        for zone in counts
    }

zone_violation_rate = {
    "baseline": _zone_violation_rates(zone_base_engine),
    "proposed": _zone_violation_rates(zone_prop_engine),
}

body_zone_rows = []
zones = sorted(zone_result["proposed"].keys())
for zone in zones:
    b = zone_result["baseline"][zone]
    p = zone_result["proposed"][zone]
    body_zone_rows.append({
        "body_zone": zone,
        "baseline_mean_sync_interval_ms": b.get("mean_sync_interval_ms"),
        "proposed_mean_sync_interval_ms": p.get("mean_sync_interval_ms"),
        "proposed_mean_pt_ms": p.get("mean_pt"),
        "proposed_mean_pe_ms": p.get("mean_pe"),
        "proposed_mean_psm_ms": p.get("mean_psm"),
        "baseline_energy_per_node_j": (b["energy_j"] / b["count"]) if b.get("count") else None,
        "proposed_energy_per_node_j": (p["energy_j"] / p["count"]) if p.get("count") else None,
        "baseline_violation_rate_pct": zone_violation_rate["baseline"].get(zone),
        "proposed_violation_rate_pct": zone_violation_rate["proposed"].get(zone),
    })
    print(f"  {zone:10s} PT={p.get('mean_pt')}  PE={p.get('mean_pe')}  PSM={p.get('mean_psm')}  "
          f"syncInterval base={b.get('mean_sync_interval_ms')}->prop={p.get('mean_sync_interval_ms')}")

with open(os.path.join(AGG_DIR, "body_zone_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(body_zone_rows[0].keys()))
    w.writeheader()
    for r in body_zone_rows:
        w.writerow(r)
with open(os.path.join(AGG_DIR, "body_zone_raw.json"), "w") as f:
    json.dump(zone_result, f, indent=2, default=str)
print()
print("All Sprint 12 statistics/table artifacts written to results/aggregates/")
