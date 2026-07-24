"""
Sprint 12 Deliverables 6, 7, 8 -- Targeted Sensitivity Analysis and the
3-way Ablation Study (Uniform / Generic-Adaptive / Full PSM System).

Sensitivity perturbations are applied via temporary, restored monkey-patches
of the already-imported module-level coefficients (contextlib contextmanager
with try/finally), so the frozen model files on disk are never touched and
every other run in this process still uses the exact frozen defaults.
"""
import contextlib
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import core.dtce as dtce_mod
import core.node_factory as node_factory_mod
import core.sce as sce_mod
import core.simulation_engine as sim_engine_mod

from core.experiment_engine import run_seed_matrix, ControlledExperiment
from core.experiment_metrics import aggregate_metric
from config.baseline_policies import DEFAULT_UNIFORM_POLICY, FULL_SEED_LIST
from config.simulation_profiles import DEFAULT_DURATION_S, DEFAULT_TIME_STEP_S

VAL_DIR = os.path.join(ROOT, "results", "validation")
os.makedirs(VAL_DIR, exist_ok=True)

NODES = 30
SCENARIO = "Scenario B: Moderate"
SEEDS = FULL_SEED_LIST[:10]


@contextlib.contextmanager
def patched(module, **kwargs):
    """Temporarily overwrite module-level attributes, always restoring them."""
    originals = {name: getattr(module, name) for name in kwargs}
    try:
        for name, value in kwargs.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


def scale_dict(d, factor):
    return {k: (v * factor if isinstance(v, (int, float)) else v) for k, v in d.items()}


def run_summary(network_profile=None):
    res = run_seed_matrix(nodes=NODES, duration=DEFAULT_DURATION_S, time_step=DEFAULT_TIME_STEP_S,
                           scenario=SCENARIO, seeds=SEEDS, baseline_policy=DEFAULT_UNIFORM_POLICY)
    # network_profile isn't a run_seed_matrix param; apply via ControlledExperiment directly if needed.
    sync_b = aggregate_metric([r["sync_messages"] for r in res["baseline"]])
    sync_p = aggregate_metric([r["sync_messages"] for r in res["proposed"]])
    energy_b = aggregate_metric([r["estimated_energy_j"] for r in res["baseline"]])
    energy_p = aggregate_metric([r["estimated_energy_j"] for r in res["proposed"]])
    viol_b = aggregate_metric([r["violation_rate_pct"] for r in res["baseline"]])
    viol_p = aggregate_metric([r["violation_rate_pct"] for r in res["proposed"]])
    psm_p = aggregate_metric([r["mean_psm"] for r in res["proposed"] if r["mean_psm"] is not None])
    sync_reduction = (sync_b["mean"] - sync_p["mean"]) / sync_b["mean"] * 100 if sync_b["mean"] else None
    energy_reduction = (energy_b["mean"] - energy_p["mean"]) / energy_b["mean"] * 100 if energy_b["mean"] else None
    viol_diff_pp = viol_p["mean"] - viol_b["mean"]
    return {
        "sync_reduction_pct": sync_reduction,
        "energy_reduction_pct": energy_reduction,
        "violation_diff_pp": viol_diff_pp,
        "mean_psm_proposed": psm_p["mean"],
    }


def run_summary_with_network(network_profile):
    baseline_metrics, proposed_metrics = [], []
    from core.experiment_metrics import compute_run_metrics
    for seed in SEEDS:
        exp = ControlledExperiment(seed=seed, nodes=NODES, duration=DEFAULT_DURATION_S,
                                    time_step=DEFAULT_TIME_STEP_S, scenario=SCENARIO,
                                    network_profile=network_profile, baseline_policy=DEFAULT_UNIFORM_POLICY)
        base_engine, prop_engine = exp.run_pair()
        baseline_metrics.append(compute_run_metrics(base_engine))
        proposed_metrics.append(compute_run_metrics(prop_engine))
    sync_b = aggregate_metric([r["sync_messages"] for r in baseline_metrics])
    sync_p = aggregate_metric([r["sync_messages"] for r in proposed_metrics])
    energy_b = aggregate_metric([r["estimated_energy_j"] for r in baseline_metrics])
    energy_p = aggregate_metric([r["estimated_energy_j"] for r in proposed_metrics])
    viol_b = aggregate_metric([r["violation_rate_pct"] for r in baseline_metrics])
    viol_p = aggregate_metric([r["violation_rate_pct"] for r in proposed_metrics])
    psm_p = aggregate_metric([r["mean_psm"] for r in proposed_metrics if r["mean_psm"] is not None])
    return {
        "sync_reduction_pct": (sync_b["mean"] - sync_p["mean"]) / sync_b["mean"] * 100 if sync_b["mean"] else None,
        "energy_reduction_pct": (energy_b["mean"] - energy_p["mean"]) / energy_b["mean"] * 100 if energy_b["mean"] else None,
        "violation_diff_pp": viol_p["mean"] - viol_b["mean"],
        "mean_psm_proposed": psm_p["mean"],
    }


t_start = time.time()
sensitivity_rows = []


def record(parameter, variation, summary, is_default):
    stable = (summary["sync_reduction_pct"] is not None and summary["sync_reduction_pct"] > 0
              and summary["violation_diff_pp"] is not None and summary["violation_diff_pp"] <= 5.0)
    sensitivity_rows.append({
        "parameter": parameter, "variation": variation,
        "sync_reduction_pct": summary["sync_reduction_pct"],
        "energy_reduction_pct": summary["energy_reduction_pct"],
        "violation_diff_pp": summary["violation_diff_pp"],
        "mean_psm_proposed": summary["mean_psm_proposed"],
        "conclusion_stable": "-" if is_default else ("Yes" if stable else "No"),
    })
    print(f"  {parameter:22s} {variation:10s} sync_red={summary['sync_reduction_pct']:.1f}% "
          f"energy_red={summary['energy_reduction_pct']:.1f}% viol_diff={summary['violation_diff_pp']:+.2f}pp "
          f"meanPSM={summary['mean_psm_proposed']:.1f} stable={'-' if is_default else ('Yes' if stable else 'No')}")


print("=== Deliverable 6/7: Targeted Sensitivity Analysis ===")
print(f"Fixed config for all sensitivity runs: nodes={NODES}, duration={DEFAULT_DURATION_S}s, "
      f"scenario={SCENARIO}, seeds={SEEDS}")

print("-- PT sensitivity (BASE_THRESHOLDS_MS scaled) --")
default_thresholds = dict(dtce_mod.BASE_THRESHOLDS_MS)
for label, factor in (("-10%", 0.9), ("Default", 1.0), ("+10%", 1.1)):
    with patched(dtce_mod, BASE_THRESHOLDS_MS=scale_dict(default_thresholds, factor)):
        summary = run_summary()
    record("PT_baseline_profile", label, summary, is_default=(label == "Default"))

print("-- Clock-drift severity (CLOCK_DRIFT_RANGE scaled) --")
default_drift_range = node_factory_mod.CLOCK_DRIFT_RANGE
for label, factor in (("Low", 0.5), ("Nominal", 1.0), ("High", 2.0)):
    scaled = tuple(v * factor for v in default_drift_range)
    with patched(node_factory_mod, CLOCK_DRIFT_RANGE=scaled):
        summary = run_summary()
    record("Clock_drift_severity", label, summary, is_default=(label == "Nominal"))

print("-- Network variability --")
print("  FINDING: DigitalTwinSimulationEngine._apply_scenario_context() resets")
print("  _active_network_profile from the scenario's own phase definition on")
print("  every cycle, so the constructor's network_profile argument has no")
print("  lasting effect once a scenario is fixed (confirmed by inspecting")
print("  core/simulation_engine.py). Genuine network-variability sensitivity is")
print("  therefore tested via the SCENARIO dimension itself, since each of the")
print("  three frozen scenarios carries its own distinct network profile.")
for label, scen in (("Scenario_A_Stable_net", "Scenario A: Stable"),
                     ("Scenario_B_Moderate_net", "Scenario B: Moderate"),
                     ("Scenario_C_Challenging_net", "Scenario C: Dynamic/Challenging")):
    res = run_seed_matrix(nodes=NODES, duration=DEFAULT_DURATION_S, time_step=DEFAULT_TIME_STEP_S,
                           scenario=scen, seeds=SEEDS, baseline_policy=DEFAULT_UNIFORM_POLICY)
    sync_b = aggregate_metric([r["sync_messages"] for r in res["baseline"]])
    sync_p = aggregate_metric([r["sync_messages"] for r in res["proposed"]])
    energy_b = aggregate_metric([r["estimated_energy_j"] for r in res["baseline"]])
    energy_p = aggregate_metric([r["estimated_energy_j"] for r in res["proposed"]])
    viol_b = aggregate_metric([r["violation_rate_pct"] for r in res["baseline"]])
    viol_p = aggregate_metric([r["violation_rate_pct"] for r in res["proposed"]])
    psm_p = aggregate_metric([r["mean_psm"] for r in res["proposed"] if r["mean_psm"] is not None])
    summary = {
        "sync_reduction_pct": (sync_b["mean"] - sync_p["mean"]) / sync_b["mean"] * 100 if sync_b["mean"] else None,
        "energy_reduction_pct": (energy_b["mean"] - energy_p["mean"]) / energy_b["mean"] * 100 if energy_b["mean"] else None,
        "violation_diff_pp": viol_p["mean"] - viol_b["mean"],
        "mean_psm_proposed": psm_p["mean"],
    }
    record("Network_variability_via_scenario", label, summary, is_default=(scen == SCENARIO))

print("-- SCE state boundaries (RELAXED_MIN / NOMINAL_MIN scaled +-10%) --")
default_relaxed, default_nominal = sce_mod.RELAXED_MIN, sce_mod.NOMINAL_MIN
for label, factor in (("-10%", 0.9), ("Default", 1.0), ("+10%", 1.1)):
    with patched(sce_mod, RELAXED_MIN=default_relaxed * factor, NOMINAL_MIN=default_nominal * factor):
        summary = run_summary()
    record("SCE_state_boundaries", label, summary, is_default=(label == "Default"))

print("-- Energy coefficients (radio-active-cost-per-second scaled) --")
default_energy_by_level = dict(sim_engine_mod.ENERGY_COST_PER_ACTIVE_SECOND_BY_LEVEL)
for label, factor in (("Lower_cost", 0.7), ("Default", 1.0), ("Higher_cost", 1.3)):
    with patched(sim_engine_mod, ENERGY_COST_PER_ACTIVE_SECOND_BY_LEVEL=scale_dict(default_energy_by_level, factor)):
        summary = run_summary()
    record("Energy_coefficients", label, summary, is_default=(label == "Default"))

print(f"Sensitivity analysis runtime: {time.time() - t_start:.1f}s")

with open(os.path.join(VAL_DIR, "sensitivity_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(sensitivity_rows[0].keys()))
    w.writeheader()
    for r in sensitivity_rows:
        w.writerow(r)
print()

# ------------------------------------------------------------------
# Deliverable 8: Ablation Study (A: Uniform / B: Generic Adaptive / C: Full PSM System)
# ------------------------------------------------------------------
print("=== Deliverable 8: Ablation Study (A/B/C) ===")
from core.experiment_metrics import compute_run_metrics as _crm

ablation_metrics = {"A_Uniform": [], "B_Generic_Adaptive": [], "C_Full_PSM_System": []}
t_abl = time.time()
for seed in SEEDS:
    exp = ControlledExperiment(seed=seed, nodes=NODES, duration=DEFAULT_DURATION_S,
                                time_step=DEFAULT_TIME_STEP_S, scenario=SCENARIO,
                                baseline_policy=DEFAULT_UNIFORM_POLICY)
    e_uniform = exp._make_engine("uniform"); e_uniform.initialize(); e_uniform.run_to_completion()
    e_generic = exp._make_engine("generic_adaptive"); e_generic.initialize(); e_generic.run_to_completion()
    e_full = exp._make_engine("adaptive"); e_full.initialize(); e_full.run_to_completion()
    ablation_metrics["A_Uniform"].append(_crm(e_uniform))
    ablation_metrics["B_Generic_Adaptive"].append(_crm(e_generic))
    ablation_metrics["C_Full_PSM_System"].append(_crm(e_full))
print(f"Ablation runtime: {time.time() - t_abl:.1f}s ({len(SEEDS)} seeds x 3 methods = {len(SEEDS)*3} runs)")

ablation_rows = []
for method, runs in ablation_metrics.items():
    sync = aggregate_metric([r["sync_messages"] for r in runs])
    energy = aggregate_metric([r["estimated_energy_j"] for r in runs])
    viol = aggregate_metric([r["violation_rate_pct"] for r in runs])
    psm = aggregate_metric([r["mean_psm"] for r in runs if r["mean_psm"] is not None])
    row = {
        "method": method,
        "sync_messages_mean": sync["mean"], "sync_messages_n": sync["n"],
        "estimated_energy_j_mean": energy["mean"],
        "violation_rate_pct_mean": viol["mean"],
        "mean_psm_mean": psm["mean"],
    }
    ablation_rows.append(row)
    print(f"  {method:22s} sync={sync['mean']:.1f}  energy={energy['mean']:.2f}J  "
          f"viol={viol['mean']:.3f}%  meanPSM={psm['mean']:.2f}")

with open(os.path.join(VAL_DIR, "ablation_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ablation_rows[0].keys()))
    w.writeheader()
    for r in ablation_rows:
        w.writerow(r)

sens_ablation_report = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "sensitivity": sensitivity_rows,
    "ablation": ablation_rows,
    "ablation_config": {"nodes": NODES, "duration_s": DEFAULT_DURATION_S, "scenario": SCENARIO, "seeds": SEEDS},
}
with open(os.path.join(VAL_DIR, "sprint12_sensitivity_ablation_report.json"), "w") as f:
    json.dump(sens_ablation_report, f, indent=2, default=str)
print()
print("All Sprint 12 sensitivity/ablation artifacts written to results/validation/")
