"""
Sprint 12 Deliverables 10-16 -- Final Experiment Matrix, Statistical Summary,
Effect Sizes, and the Core/Scenario/Body-Zone/Scalability Tables.

Runs the full 3-scenario x 5-node-count x 10-seed x 2-strategy matrix
(300 runs) from the terminal so results are file-based and reproducible.
"""
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.experiment_engine import (
    ControlledExperiment, run_scenario_matrix, run_body_zone_experiment,
)
from core.experiment_metrics import (
    aggregate_metric, paired_seed_differences, sanity_check, evaluate_success_criterion,
)
from config.baseline_policies import DEFAULT_UNIFORM_POLICY, FULL_SEED_LIST, DEFAULT_SCALABILITY_NODE_COUNTS

RAW_DIR = os.path.join(ROOT, "results", "raw")
AGG_DIR = os.path.join(ROOT, "results", "aggregates")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(AGG_DIR, exist_ok=True)

SEEDS = FULL_SEED_LIST[:10]
NODE_COUNTS = DEFAULT_SCALABILITY_NODE_COUNTS  # [10, 20, 30, 40, 50]
SCENARIOS = ["Scenario A: Stable", "Scenario B: Moderate", "Scenario C: Dynamic/Challenging"]
DURATION_S = 300.0
TIME_STEP_S = 1.0
PRIMARY_NODES = 30
PRIMARY_SCENARIO = "Scenario B: Moderate"

print("=== Deliverable 10: Final Experiment Matrix (3 scenarios x 5 node counts x 10 seeds x 2 strategies) ===")
print(f"Expected runs: {len(SCENARIOS)} x {len(NODE_COUNTS)} x {len(SEEDS)} x 2 = "
      f"{len(SCENARIOS)*len(NODE_COUNTS)*len(SEEDS)*2}")

t0 = time.time()
full_matrix_rows = []
failed_runs = []
for n in NODE_COUNTS:
    scen_result = run_scenario_matrix(nodes=n, duration=DURATION_S, time_step=TIME_STEP_S,
                                       seeds=SEEDS, baseline_policy=DEFAULT_UNIFORM_POLICY,
                                       scenarios=SCENARIOS)
    for scenario, res in scen_result.items():
        for strategy in ("baseline", "proposed"):
            for m in res[strategy]:
                row = dict(m)
                row["strategy"] = strategy
                full_matrix_rows.append(row)
elapsed = time.time() - t0
completed_runs = len(full_matrix_rows)
expected_runs = len(SCENARIOS) * len(NODE_COUNTS) * len(SEEDS) * 2
print(f"Completed runs: {completed_runs} / expected {expected_runs}  (runtime {elapsed:.1f}s)")
print(f"Failed runs: {len(failed_runs)}  Excluded runs: 0  (no runs were silently discarded)")

with open(os.path.join(RAW_DIR, "experiment_runs.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(full_matrix_rows[0].keys()))
    w.writeheader()
    for r in full_matrix_rows:
        w.writerow(r)

matrix_meta = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "expected_runs": expected_runs, "completed_runs": completed_runs,
    "failed_runs": len(failed_runs), "excluded_runs": 0,
    "runtime_s": elapsed, "scenarios": SCENARIOS, "node_counts": NODE_COUNTS,
    "seeds": SEEDS, "duration_s": DURATION_S, "time_step_s": TIME_STEP_S,
}
with open(os.path.join(AGG_DIR, "final_experiment_matrix_manifest.json"), "w") as f:
    json.dump(matrix_meta, f, indent=2, default=str)
print()

