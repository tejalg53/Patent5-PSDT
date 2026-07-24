"""
Sprint 12 Deliverables 1-2 -- Freeze the Final Model Version & Configuration Manifest.

Reads every parameter that affects results directly from the live, frozen
source modules (never hand-copied), so the manifest can never drift from the
actual running code. Writes results/configuration/final_configuration.json
and results/configuration/model_version.txt. Read-only: does not modify any
core/ or config/ file.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FINAL_MODEL_VERSION = "PSDT v1.0 Patent 5 Experimental Validation Build"

import core.constants as constants
import core.threshold_profiles as threshold_profiles
import core.error_profiles as error_profiles
import core.sce as sce
import config.state_boundaries as state_boundaries
import config.resource_profiles as resource_profiles
import config.energy_model as energy_model
import config.simulation_profiles as simulation_profiles
import config.baseline_policies as baseline_policies


def jsonable(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return True
    if isinstance(value, (list, tuple)):
        return all(jsonable(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, (str, int)) for k in value) and all(jsonable(v) for v in value.values())
    return False


def to_jsonable(value):
    if isinstance(value, tuple):
        return [to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return value


def dump_module(mod):
    out = {}
    for name in dir(mod):
        if name.startswith("_"):
            continue
        val = getattr(mod, name)
        if callable(val) or isinstance(val, type):
            continue
        if str(type(val).__module__) not in ("builtins",):
            continue
        if jsonable(val):
            out[name] = to_jsonable(val)
    return out


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    except Exception:
        return "unknown"


manifest = {
    "model_version": FINAL_MODEL_VERSION,
    "frozen_sprint11_model_version": baseline_policies.MODEL_VERSION,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "git_commit": git_commit(),
    "python_version": sys.version,

    "dtce_parameters": {
        "formula": "PTz(t) = PTbase,z x Ff x Fa x UCF x Fm x Fe (see core/dtce.py DynamicThresholdCharacterizationEngine.compute_threshold)",
        "zone_topology": dump_module(constants),
        "threshold_coefficients": dump_module(threshold_profiles),
    },

    "peee_parameters": {
        "formula": "PEz(t) estimated from clock-drift (CD), network-residual (ND), actuator-driver-delay (AD), and mechanical-startup-delay (MD) components combined per the selected error model (default 'additive'), see core/peee.py PerceivedErrorEstimationEngine.compute_error",
        "error_model_defaults_and_bounds": dump_module(error_profiles),
    },

    "psme_parameters": {
        "psm_formula": "PSMz(t) = PTz(t) - PEz(t)",
        "npsm_formula": "NPSMz(t) = PSMz(t) / PTz(t)",
        "tu_formula": "TUz(t) = (PEz(t) / PTz(t)) * 100",
        "note": "PSME (core/psme.py) is pure arithmetic on PT/PE; it has no separate tunable coefficients of its own.",
    },

    "sce_parameters": {
        "state_labels": {
            "RELAXED": sce.RELAXED, "NOMINAL": sce.NOMINAL,
            "ELEVATED": sce.ELEVATED, "IMMEDIATE": sce.IMMEDIATE,
        },
        "state_order_most_to_least_relaxed": list(sce.STATE_ORDER),
        "boundaries_and_hysteresis": dump_module(state_boundaries),
    },

    "arac_parameters": dump_module(resource_profiles),

    "energy_model": dump_module(energy_model),

    "simulation_parameters": dump_module(simulation_profiles),

    "baseline_policy": dump_module(baseline_policies),
}

config_json = json.dumps(manifest, indent=2, sort_keys=True, default=str)
config_hash = hashlib.sha256(config_json.encode("utf-8")).hexdigest().upper()
configuration_id = f"PSDT-V1-CFG-{config_hash[:8]}"
manifest["configuration_id"] = configuration_id
manifest["configuration_sha256"] = config_hash

OUT_DIR = os.path.join(ROOT, "results", "configuration")
os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "final_configuration.json"), "w") as f:
    json.dump(manifest, f, indent=2, sort_keys=True, default=str)

with open(os.path.join(OUT_DIR, "model_version.txt"), "w") as f:
    f.write(FINAL_MODEL_VERSION + "\n")
    f.write(f"Configuration ID: {configuration_id}\n")
    f.write(f"Frozen Sprint 11 model version: {baseline_policies.MODEL_VERSION}\n")
    f.write(f"Git commit: {manifest['git_commit']}\n")
    f.write(f"Generated: {manifest['timestamp_utc']}\n")

print(f"Model version: {FINAL_MODEL_VERSION}")
print(f"Configuration ID: {configuration_id}")
print(f"Git commit: {manifest['git_commit']}")
print(f"Written to {OUT_DIR}/final_configuration.json")
