"""
Sprint 12 Deliverable 20 -- Export Complete Evidence Package.

This script does two things, both purely from already-frozen/derived data
(no new modeling, no manually invented numbers):

1. Generates the four node/time-series-level raw_data files that are not
   already produced by the 300-run experiment matrix (which only stores
   run-level aggregates in results/raw/experiment_runs.csv): node_metrics.csv,
   time_series.csv, state_transitions.csv, resource_allocations.csv. These
   come from ONE fully-instrumented representative run at the frozen primary
   configuration (Nodes=30, Duration=300s, dt=1s, Scenario=Moderate, Seed=42
   -- the same representative configuration used for the Deliverable 3
   reproducibility audit), for both the Uniform Baseline and PSM-Adaptive
   strategies.
2. Assembles PSDT_Patent5_Final_Evidence/ (and a matching .zip) containing
   configuration/, raw_data/, summaries/, validation/, figures/, and a
   README.txt, by copying files that already exist on disk.
"""
import csv
import json
import os
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.experiment_engine import ControlledExperiment
from config.baseline_policies import DEFAULT_UNIFORM_POLICY

RESULTS_DIR = os.path.join(ROOT, "results")
RAW_DIR = os.path.join(RESULTS_DIR, "raw")
AGG_DIR = os.path.join(RESULTS_DIR, "aggregates")
VAL_DIR = os.path.join(RESULTS_DIR, "validation")
CFG_DIR = os.path.join(RESULTS_DIR, "configuration")
FIG_DIR = os.path.join(RESULTS_DIR, "figures")
os.makedirs(RAW_DIR, exist_ok=True)

PRIMARY_NODES = 30
PRIMARY_DURATION_S = 300.0
PRIMARY_TIME_STEP_S = 1.0
PRIMARY_SCENARIO = "Scenario B: Moderate"
PRIMARY_SEED = 42

with open(os.path.join(CFG_DIR, "final_configuration.json")) as f:
    CONFIG = json.load(f)


def log(msg):
    print(msg, flush=True)


t0 = time.time()


# ---------------------------------------------------------------------------
# Step 1: generate node_metrics / time_series / state_transitions / resource_allocations
# from ONE fully-instrumented representative paired run.
# ---------------------------------------------------------------------------
log("=== Sprint 12 Deliverable 20: generating node/time-series raw-data files ===")
exp = ControlledExperiment(
    seed=PRIMARY_SEED, nodes=PRIMARY_NODES, duration=PRIMARY_DURATION_S,
    time_step=PRIMARY_TIME_STEP_S, scenario=PRIMARY_SCENARIO,
    baseline_policy=DEFAULT_UNIFORM_POLICY,
)
base_engine, prop_engine = exp.run_pair()
engines = {"Uniform": base_engine, "PSM-Adaptive": prop_engine}

node_metrics_rows = []
time_series_rows = []
resource_rows = []
state_transition_rows = []

for strategy, engine in engines.items():
    registry = engine.coordinator.registry
    for node_id, node in registry.items():
        zone = node.body_zone
        series = engine.history.node_dataframe_dict(node_id)
        n = len(series.get("timestamp", []))
        prev_state = None
        for i in range(n):
            step = series["step"][i]
            ts = series["timestamp"][i]
            state = series["current_state"][i]
            time_series_rows.append({
                "strategy": strategy, "node_id": node_id, "body_zone": zone,
                "step": step, "timestamp": ts,
                "PT": series["PT"][i], "PE": series["PE"][i], "PSM": series["PSM"][i],
                "NPSM": series["NPSM"][i], "TU": series["TU"][i], "current_state": state,
            })
            resource_rows.append({
                "strategy": strategy, "node_id": node_id, "body_zone": zone,
                "step": step, "timestamp": ts,
                "sync_interval_ms": series["sync_interval_ms"][i],
                "beacon_interval_ms": series["beacon_interval_ms"][i],
                "radio_wakeup_interval_ms": series["radio_wakeup_interval_ms"][i],
                "tx_power_pct": series["tx_power_pct"][i],
                "trigger_offset_ms": series["trigger_offset_ms"][i],
            })
            if prev_state is not None and state != prev_state:
                state_transition_rows.append({
                    "strategy": strategy, "node_id": node_id, "body_zone": zone,
                    "step": step, "timestamp": ts,
                    "from_state": prev_state, "to_state": state,
                })
            prev_state = state
        node_metrics_rows.append({
            "strategy": strategy, "node_id": node_id, "body_zone": zone,
            "actuator_type": node.actuator_type,
            "final_PT": node.perceptual_threshold, "final_PE": node.perceived_error,
            "final_PSM": node.psm, "final_NPSM": node.normalized_psm,
            "final_TU": node.threshold_utilization_pct, "final_state": node.sync_state,
            "battery_level_pct": node.battery_level,
            "radio_active_time_s": node.radio_active_time,
            "energy_consumed_j": node.energy_consumed,
            "packet_count": node.packet_count,
            "allocated_sync_interval_ms": node.allocated_sync_interval_ms,
            "allocated_beacon_interval_ms": node.allocated_beacon_interval_ms,
            "allocated_radio_wakeup_interval_ms": node.allocated_radio_wakeup_interval_ms,
            "allocated_transmit_power_pct": node.allocated_transmit_power_pct,
            "allocated_trigger_offset_ms": node.allocated_trigger_offset_ms,
        })


def write_csv(path, rows):
    if not rows:
        with open(path, "w") as f:
            f.write("")
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)


write_csv(os.path.join(RAW_DIR, "node_metrics.csv"), node_metrics_rows)
write_csv(os.path.join(RAW_DIR, "time_series.csv"), time_series_rows)
write_csv(os.path.join(RAW_DIR, "state_transitions.csv"), state_transition_rows)
write_csv(os.path.join(RAW_DIR, "resource_allocations.csv"), resource_rows)
log(f"  node_metrics.csv: {len(node_metrics_rows)} rows ({PRIMARY_NODES} nodes x 2 strategies)")
log(f"  time_series.csv: {len(time_series_rows)} rows")
log(f"  state_transitions.csv: {len(state_transition_rows)} rows")
log(f"  resource_allocations.csv: {len(resource_rows)} rows")
log(
    "  NOTE: node_metrics/time_series/state_transitions/resource_allocations are from ONE "
    "fully-instrumented representative paired run at the frozen primary configuration "
    f"(Nodes={PRIMARY_NODES}, Duration={PRIMARY_DURATION_S}s, dt={PRIMARY_TIME_STEP_S}s, "
    f"Scenario={PRIMARY_SCENARIO}, Seed={PRIMARY_SEED}). experiment_runs.csv separately holds "
    "run-level aggregates for the full 300-run matrix."
)

# ---------------------------------------------------------------------------
# Step 2: assemble the PSDT_Patent5_Final_Evidence/ package + matching .zip
# ---------------------------------------------------------------------------
log("\n=== Assembling PSDT_Patent5_Final_Evidence package ===")
PKG_NAME = "PSDT_Patent5_Final_Evidence"
PKG_DIR = os.path.join(ROOT, "exports", PKG_NAME)
if os.path.exists(PKG_DIR):
    shutil.rmtree(PKG_DIR)
os.makedirs(PKG_DIR, exist_ok=True)

for sub in ("configuration", "raw_data", "summaries", "validation", "figures"):
    os.makedirs(os.path.join(PKG_DIR, sub), exist_ok=True)


def _copy(src, dst_dir, required=True):
    if os.path.exists(src):
        shutil.copy2(src, dst_dir)
    elif required:
        log(f"  WARNING: missing expected file {src}")


_copy(os.path.join(CFG_DIR, "final_configuration.json"), os.path.join(PKG_DIR, "configuration"))
_copy(os.path.join(CFG_DIR, "model_version.txt"), os.path.join(PKG_DIR, "configuration"))

for name in ("experiment_runs.csv", "node_metrics.csv", "time_series.csv",
             "state_transitions.csv", "resource_allocations.csv"):
    _copy(os.path.join(RAW_DIR, name), os.path.join(PKG_DIR, "raw_data"))

for name in ("core_results.csv", "scenario_results.csv", "body_zone_results.csv",
             "scalability_results.csv"):
    _copy(os.path.join(AGG_DIR, name), os.path.join(PKG_DIR, "summaries"))
for name in ("sensitivity_results.csv", "ablation_results.csv"):
    _copy(os.path.join(VAL_DIR, name), os.path.join(PKG_DIR, "summaries"))

for name in ("reproducibility_report.csv", "invariant_audit.csv", "baseline_fairness.csv"):
    _copy(os.path.join(VAL_DIR, name), os.path.join(PKG_DIR, "validation"))
_copy(os.path.join(VAL_DIR, "traceability_test.csv"), os.path.join(PKG_DIR, "validation"), required=False)

for name in ("sync_messages.png", "estimated_energy.png", "violation_rate.png",
             "body_zone_sync.png", "disturbance_response.png", "scalability.png"):
    _copy(os.path.join(FIG_DIR, name), os.path.join(PKG_DIR, "figures"))
    _copy(os.path.join(FIG_DIR, f"{os.path.splitext(name)[0]}.provenance.json"),
          os.path.join(PKG_DIR, "figures"), required=False)

manifest = {}
manifest_path = os.path.join(AGG_DIR, "final_experiment_matrix_manifest.json")
if os.path.exists(manifest_path):
    with open(manifest_path) as f:
        manifest = json.load(f)

success = {}
success_path = os.path.join(AGG_DIR, "success_criterion.json")
if os.path.exists(success_path):
    with open(success_path) as f:
        success = json.load(f)

readme = f"""PSDT Patent 5 -- Final Evidence Package
=======================================
Generated: {datetime.now(timezone.utc).isoformat()}

Model Version:      {CONFIG.get('model_version')}
Configuration ID:    {CONFIG.get('configuration_id')}
Configuration SHA256: {CONFIG.get('configuration_sha256')}
Frozen at git commit: {CONFIG.get('git_commit')}

What PSDT simulates
-------------------
PSDT (Perceptual Synchronization Digital Twin) is a software simulation of a distributed
wearable haptic network (Patent 5). Each simulated node represents a haptic actuator at a
body zone (Fingertip, Hand, Forearm, Torso, Leg, Foot). The simulation models, per node and
per time step: a Dynamic Threshold Computation Engine (DTCE) estimating a perceptual
threshold PT(t); a Perceptual Error Estimation Engine (PEEE) estimating perceived
synchronization error PE(t); a Perceptual Synchronization Margin Engine (PSME) computing
PSM(t) = PT(t) - PE(t) and its normalized/utilization forms; a State Classification Engine
(SCE) assigning an operational state from PSM with hysteresis; and an Adaptive Resource
Allocation Controller (ARAC) that maps state to synchronization/beacon/wake-up intervals,
transmit power, and trigger offsets, applied via a placeholder Resource Application layer
(PRAP). An energy-accounting model estimates communication energy from radio-active time.

Uniform Baseline vs PSM-Adaptive
---------------------------------
The Uniform Baseline applies one fixed synchronization/resource policy to every node,
regardless of body zone or measured PSM. The PSM-Adaptive ("proposed", full Patent 5) system
drives resource allocation from each node's own body-zone-specific PSM via the SCE/ARAC chain
described above. Both strategies are run with identical seeds, node/body-zone/actuator
distributions, drift and network-disturbance sequences, context/scenario timelines, duration,
and energy coefficients -- only the synchronization/resource-control strategy differs
(see validation/baseline_fairness.csv).

How experiments were paired
---------------------------
For every (scenario, node-count, seed) combination, a Uniform run and a PSM-Adaptive run are
constructed from the same seed and configuration and executed step-by-step in parallel
(paired design), so any difference in outcome is attributable to the control strategy alone.
The frozen final experiment matrix is 3 scenarios x 5 node counts x 10 seeds x 2 strategies
= 300 runs (see raw_data/experiment_runs.csv and this manifest: expected={manifest.get('expected_runs')},
completed={manifest.get('completed_runs')}, failed={manifest.get('failed_runs')},
excluded={manifest.get('excluded_runs')}).

How to interpret violation rate
--------------------------------
"Violation rate" is the modeled percentage of observed time steps where PSM(t) < 0, i.e. the
estimated perceived synchronization error exceeded the modeled perceptual threshold for that
node at that step. It is a simulation-internal quantity computed from PT(t) and PE(t) as
modeled by DTCE/PEEE -- it is not a measurement of human perception. Both a relative
percentage change and an absolute percentage-point change are reported where relevant, since
absolute pp changes are clearer than relative percentages alone for small baseline rates.

Pre-registered success criterion: success={success.get('success')},
energy_reduced={success.get('energy_reduced')}, messages_reduced={success.get('messages_reduced')},
violation_diff_pp={success.get('violation_diff_pp')}, tolerance_pp={success.get('tolerance_pp')}.

What is simulated vs experimentally measured
---------------------------------------------
EVERYTHING in this package is produced by a software simulation (PSDT). PT, PE, PSM, states,
resource allocations, and energy are all modeled/estimated quantities computed by the code in
core/ under the frozen configuration in configuration/final_configuration.json. These are
simulation validation results, not physical hardware measurements and not human-subject
clinical or perceptual validation. No claim in this package should be read as a measurement of
real human perception, real radio hardware, or real battery life.

Package contents
----------------
configuration/   final_configuration.json, model_version.txt -- the frozen model/parameter set
raw_data/        experiment_runs.csv (300-run matrix, run-level) plus node_metrics.csv,
                 time_series.csv, state_transitions.csv, resource_allocations.csv (node- and
                 time-step-level detail from one fully-instrumented representative run at the
                 frozen primary configuration: Nodes=30, Duration=300s, dt=1s,
                 Scenario=Moderate, Seed=42, both strategies)
summaries/       core_results.csv, scenario_results.csv, body_zone_results.csv,
                 scalability_results.csv, sensitivity_results.csv, ablation_results.csv
validation/      reproducibility_report.csv, invariant_audit.csv, baseline_fairness.csv,
                 traceability_test.csv
figures/         sync_messages.png, estimated_energy.png, violation_rate.png,
                 body_zone_sync.png, disturbance_response.png, scalability.png (each with a
                 matching *.provenance.json carrying Model Version, Configuration ID,
                 scenario/node-count/seeds/strategies, and generation timestamp)
"""

with open(os.path.join(PKG_DIR, "README.txt"), "w") as f:
    f.write(readme)

zip_path = os.path.join(ROOT, "exports", f"{PKG_NAME}.zip")
if os.path.exists(zip_path):
    os.remove(zip_path)
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for dirpath, _, filenames in os.walk(PKG_DIR):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            arcname = os.path.join(PKG_NAME, os.path.relpath(full, PKG_DIR))
            zf.write(full, arcname)

n_files = sum(len(fn) for _, _, fn in os.walk(PKG_DIR))
log(f"  Package assembled at {PKG_DIR} ({n_files} files)")
log(f"  Zip written to {zip_path} ({os.path.getsize(zip_path)} bytes)")
log(f"=== Deliverable 20 complete in {time.time() - t0:.1f}s ===")
