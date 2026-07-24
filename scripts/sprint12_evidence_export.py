"""
Sprint 12 -- Evidence Export & Reproducibility Audit.

Runs every Sprint 11 experiment type from the terminal (not the interactive
Streamlit session_state), so results are file-based, reproducible, and
independent of any browser session. Writes raw per-run data, aggregated
tables, a reproducibility/determinism check, a sensitivity check, and a
manifest documenting exactly how the numbers were produced.

Does NOT modify core/config model files. Read-only with respect to the
frozen model (MODEL_VERSION below must match the Sprint 11 frozen tag).
"""
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.experiment_engine import (
    ControlledExperiment,
    run_seed_matrix,
    run_scenario_matrix,
    run_body_zone_experiment,
    run_disturbance_experiment,
)
from core.experiment_metrics import (
    aggregate_metric,
    paired_seed_differences,
    sanity_check,
    evaluate_success_criterion,
)
from config.baseline_policies import (
    MODEL_VERSION,
    DEFAULT_UNIFORM_POLICY,
    UNIFORM_POLICY_OPTIONS,
    FULL_SEED_LIST,
    DEFAULT_SCALABILITY_NODE_COUNTS,
    VIOLATION_RATE_TOLERANCE_PP,
)
from config.simulation_profiles import (
    DEFAULT_DURATION_S,
    DEFAULT_TIME_STEP_S,
)

RESULTS_DIR = os.path.join(ROOT, "results")
RAW_DIR = os.path.join(RESULTS_DIR, "raw")
AGG_DIR = os.path.join(RESULTS_DIR, "aggregates")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(AGG_DIR, exist_ok=True)

SCENARIOS = ["Scenario A: Stable", "Scenario B: Moderate", "Scenario C: Dynamic/Challenging"]


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    except Exception:
        return "unknown"


def save_csv(path, rows):
    if not rows:
        open(path, "w").close()
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


LOG_LINES = []


def log(msg):
    print(msg, flush=True)
    LOG_LINES.append(msg)


t0 = time.time()
log(f"=== Sprint 12 evidence export starting {datetime.now(timezone.utc).isoformat()} ===")
log(f"Model version: {MODEL_VERSION}")
commit = git_commit()
log(f"Git commit: {commit}")

SEEDS10 = FULL_SEED_LIST[:10]
log(f"Seeds used (10): {SEEDS10}")
