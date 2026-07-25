"""
Sprint 12 Deliverable 19 -- Final Validation Dashboard.

Reads the frozen configuration manifest and the Sprint 12 validation /
aggregate artifacts already written to disk by the sprint12_*.py scripts
(no re-computation, no hard-coded pass/fail badges). Every status shown
here is derived directly from those files.
"""
import json
import os

import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_DIR = os.path.join(ROOT, "results", "configuration")
AGG_DIR = os.path.join(ROOT, "results", "aggregates")
VAL_DIR = os.path.join(ROOT, "results", "validation")
RAW_DIR = os.path.join(ROOT, "results", "raw")
FIG_DIR = os.path.join(ROOT, "results", "figures")


def _load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def _load_csv(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def _bool_col_all_true(df, col):
    if df.empty or col not in df.columns:
        return None
    return bool(df[col].astype(str).str.strip().str.lower().eq("true").all())


def status_badge(label, ok, detail=""):
    text = f"{label}: {{}}  {detail}".rstrip()
    if ok is True:
        st.success(text.format("PASS"))
    elif ok is False:
        st.error(text.format("FAIL"))
    else:
        st.warning(text.format("WARNING (could not be determined -- see detail below)"))


st.title("Final Validation -- Sprint 12 Evidence Freeze")
st.caption(
    "This page is the single source of truth for whether the frozen PSDT Patent 5 model, its "
    "300-run experiment matrix, and every downstream table/graph are reproducible, internally "
    "consistent, and fairly compared. All statuses below are computed from the actual audit "
    "artifacts in results/validation and results/aggregates -- not hard-coded."
)

config = _load_json(os.path.join(CFG_DIR, "final_configuration.json"))
manifest = _load_json(os.path.join(AGG_DIR, "final_experiment_matrix_manifest.json"))
success = _load_json(os.path.join(AGG_DIR, "success_criterion.json"))

col1, col2, col3 = st.columns(3)
col1.metric("Model Version", config.get("model_version", "n/a"))
col2.metric("Configuration ID", config.get("configuration_id", "n/a"))
col3.metric("Frozen at Git Commit", str(config.get("git_commit", "n/a"))[:12])
st.caption(
    f"Configuration SHA-256: `{config.get('configuration_sha256', 'n/a')}`  |  "
    f"Frozen: {config.get('timestamp_utc', 'n/a')}"
)

st.divider()
st.subheader("Final Experiment Matrix (Deliverable 10)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Expected Runs", manifest.get("expected_runs", "n/a"))
c2.metric("Completed Runs", manifest.get("completed_runs", "n/a"))
c3.metric("Failed Runs", manifest.get("failed_runs", "n/a"))
c4.metric("Excluded Runs", manifest.get("excluded_runs", "n/a"))
matrix_ok = (manifest.get("completed_runs") == manifest.get("expected_runs")
             and not manifest.get("failed_runs") and not manifest.get("excluded_runs"))
status_badge("Experiment Matrix", matrix_ok if manifest else None,
             "(no runs silently discarded)" if matrix_ok else "")
if manifest.get("failed_runs") or manifest.get("excluded_runs"):
    st.json({k: v for k, v in manifest.items() if "reason" in k.lower() or "fail" in k.lower() or "exclu" in k.lower()})

st.divider()
st.subheader("Validation Status")

repro_df = _load_csv(os.path.join(VAL_DIR, "reproducibility_report.csv"))
repro_ok = _bool_col_all_true(repro_df, "match")
status_badge("Reproducibility Audit (Deliverable 3)", repro_ok, f"({len(repro_df)} metrics/series compared across duplicate runs)")
with st.expander("Reproducibility detail"):
    st.dataframe(repro_df, use_container_width=True)

invariant_df = _load_csv(os.path.join(VAL_DIR, "invariant_audit.csv"))
invariant_ok = len(invariant_df) == 0
status_badge("Mathematical Invariant Audit (Deliverable 4)", invariant_ok, f"({len(invariant_df)} unexplained violations found)")
with st.expander("Invariant violations (expected: empty)"):
    st.dataframe(invariant_df, use_container_width=True)

fairness_df = _load_csv(os.path.join(VAL_DIR, "baseline_fairness.csv"))
fairness_ok = _bool_col_all_true(fairness_df, "pass")
status_badge("Baseline Fairness Audit (Deliverable 9)", fairness_ok, f"({len(fairness_df)} checks)")
with st.expander("Baseline fairness detail"):
    st.dataframe(fairness_df, use_container_width=True)

traceability_df = _load_csv(os.path.join(VAL_DIR, "traceability_test.csv"))
with st.expander(f"End-to-End Traceability (Deliverable 5) -- {len(traceability_df)} node(s) traced"):
    st.dataframe(traceability_df, use_container_width=True)

sensitivity_df = _load_csv(os.path.join(VAL_DIR, "sensitivity_results.csv"))
sens_ok = None
if not sensitivity_df.empty and "conclusion_stable" in sensitivity_df.columns:
    variations = sensitivity_df[sensitivity_df["conclusion_stable"].isin(["Yes", "No"])]
    if not variations.empty:
        sens_ok = bool((variations["conclusion_stable"] == "Yes").all())
status_badge("Sensitivity Analysis (Deliverables 6-7)", sens_ok,
             "(technical effect persists across all tested parameter variations)" if sens_ok else "")
with st.expander("Sensitivity detail"):
    st.dataframe(sensitivity_df, use_container_width=True)

ablation_df = _load_csv(os.path.join(VAL_DIR, "ablation_results.csv"))
st.info("Ablation Study (Deliverable 8): A = Uniform, B = Generic-Adaptive, C = Full Patent-5 System. "
        "Results reported as observed -- not forced into any particular ranking.")
with st.expander("Ablation detail"):
    st.dataframe(ablation_df, use_container_width=True)

st.divider()
st.subheader("Pre-Registered Success Criterion")
if success:
    status_badge("Pre-registered success criterion", success.get("success"),
                 f"(energy_reduced={success.get('energy_reduced')}, messages_reduced={success.get('messages_reduced')}, "
                 f"violation_diff_pp={success.get('violation_diff_pp'):.3f}, tolerance_pp={success.get('tolerance_pp')}, "
                 f"within_tolerance={success.get('within_tolerance')})" if success.get("violation_diff_pp") is not None else "")
else:
    st.warning("No success-criterion file found.")

st.divider()
st.subheader("Final Results Tables (Deliverables 13-16)")
tabs = st.tabs(["Core Results", "Scenario Results", "Body-Zone Results", "Scalability Results"])
with tabs[0]:
    st.dataframe(_load_csv(os.path.join(AGG_DIR, "core_results.csv")), use_container_width=True)
with tabs[1]:
    st.dataframe(_load_csv(os.path.join(AGG_DIR, "scenario_results.csv")), use_container_width=True)
with tabs[2]:
    st.dataframe(_load_csv(os.path.join(AGG_DIR, "body_zone_results.csv")), use_container_width=True)
with tabs[3]:
    st.dataframe(_load_csv(os.path.join(AGG_DIR, "scalability_results.csv")), use_container_width=True)

st.divider()
st.subheader("Final Graph Set (Deliverables 17-18)")
fig_cols = st.columns(3)
fig_names = ["sync_messages", "estimated_energy", "violation_rate", "body_zone_sync", "disturbance_response", "scalability"]
for i, name in enumerate(fig_names):
    p = os.path.join(FIG_DIR, f"{name}.png")
    if os.path.exists(p):
        fig_cols[i % 3].image(p, caption=name.replace("_", " ").title(), use_container_width=True)

