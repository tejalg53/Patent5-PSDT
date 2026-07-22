import streamlit as st
import pandas as pd

from core.experiment_engine import run_seed_matrix
from core.experiment_metrics import aggregate_metric, compare_runs, sanity_check, evaluate_success_criterion
from config.baseline_policies import (
    MODEL_VERSION,
    UNIFORM_POLICY_OPTIONS,
    DEFAULT_UNIFORM_POLICY,
    FULL_SEED_LIST,
)
from config.simulation_profiles import (
    DEFAULT_DURATION_S,
    DURATION_OPTIONS_S,
    DEFAULT_TIME_STEP_S,
    SCENARIO_OPTIONS,
    DEFAULT_SCENARIO,
)

# Sprint 11: Controlled Experimental Comparison dashboard (Deliverable 12).
# Replaces the Sprint 9 single-snapshot Before/After ARAC panel with a real
# paired-experiment runner: Uniform Baseline vs PSM-Adaptive Proposed,
# executed under identical conditions apart from control_mode (Deliverable 4).

NODE_COUNT_OPTIONS = [10, 20, 30, 40, 50]

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">Comparison</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Sprint 11 controlled experimental comparison: Uniform Synchronization baseline "
    "vs PSM-Adaptive proposed method, run in identical paired conditions (same seed, "
    "node count, scenario, duration - only the control strategy differs)."
)
st.markdown("<br>", unsafe_allow_html=True)

st.markdown('<div class="psdt-section-heading">Experiment Configuration</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    num_nodes = st.selectbox("Nodes", NODE_COUNT_OPTIONS, index=NODE_COUNT_OPTIONS.index(30))
with c2:
    duration_s = st.selectbox(
        "Duration (s)", DURATION_OPTIONS_S, index=DURATION_OPTIONS_S.index(DEFAULT_DURATION_S)
    )
with c3:
    scenario = st.selectbox("Scenario", SCENARIO_OPTIONS, index=SCENARIO_OPTIONS.index(DEFAULT_SCENARIO))
with c4:
    seed_count_options = list(range(1, len(FULL_SEED_LIST) + 1))
    num_seeds = st.selectbox("Seeds", seed_count_options, index=len(seed_count_options) - 1)
with c5:
    baseline_policy = st.selectbox(
        "Baseline Policy", UNIFORM_POLICY_OPTIONS, index=UNIFORM_POLICY_OPTIONS.index(DEFAULT_UNIFORM_POLICY)
    )

run_clicked = st.button("Run Controlled Experiment", type="primary")

if run_clicked:
    seeds = FULL_SEED_LIST[:num_seeds]
    with st.spinner(f"Running {num_seeds} paired seed(s) x 2 strategies ({num_seeds * 2} simulation runs)..."):
        raw_results = run_seed_matrix(
            nodes=num_nodes,
            duration=duration_s,
            time_step=DEFAULT_TIME_STEP_S,
            scenario=scenario,
            seeds=seeds,
            baseline_policy=baseline_policy,
        )
    st.session_state["exp11_results"] = raw_results
    st.session_state["exp11_config"] = {
        "nodes": num_nodes,
        "duration_s": duration_s,
        "scenario": scenario,
        "seeds": seeds,
        "baseline_policy": baseline_policy,
    }

results = st.session_state.get("exp11_results")
config_used = st.session_state.get("exp11_config")

if not results:
    st.info(
        "Configure the experiment above and click **Run Controlled Experiment** to generate the "
        "comparison table. No results are hard-coded here; every value below comes from a "
        "completed simulation run (Sprint 11 Deliverable 13)."
    )
else:
    baseline_runs = results["baseline"]
    proposed_runs = results["proposed"]
    n_seeds_run = len(baseline_runs)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="psdt-section-heading">Experiment Metadata</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Paired seeds", n_seeds_run)
    m2.metric("Nodes", config_used["nodes"])
    m3.metric("Duration", f'{config_used["duration_s"]} s')
    m4.metric("Scenario", config_used["scenario"].split(":")[0])
    st.caption(
        f"Model version: {MODEL_VERSION}. Baseline policy: {config_used['baseline_policy']}. "
        f"Seeds used: {config_used['seeds']}."
    )

    metric_keys = [
        "sync_messages",
        "radio_active_time_s",
        "estimated_energy_j",
        "violation_rate_pct",
        "mean_psm",
        "min_psm",
        "state_transitions",
        "mean_sync_interval_ms",
    ]
    baseline_means = {k: aggregate_metric([r[k] for r in baseline_runs])["mean"] for k in metric_keys}
    proposed_means = {k: aggregate_metric([r[k] for r in proposed_runs])["mean"] for k in metric_keys}
    cmp = compare_runs(baseline_means, proposed_means)

    def _fmt(v, digits=2):
        return "-" if v is None else round(v, digits)

    rows = [
        (
            "Sync Messages (mean per run)",
            baseline_means["sync_messages"],
            proposed_means["sync_messages"],
            cmp["sync_messages"]["reduction_pct"],
            "% reduction",
        ),
        (
            "Radio-Active Time (s, mean per run)",
            baseline_means["radio_active_time_s"],
            proposed_means["radio_active_time_s"],
            cmp["radio_active_time_s"]["reduction_pct"],
            "% reduction",
        ),
        (
            "Estimated Energy (J, mean per run)",
            baseline_means["estimated_energy_j"],
            proposed_means["estimated_energy_j"],
            cmp["estimated_energy_j"]["reduction_pct"],
            "% reduction",
        ),
        (
            "Violation Rate (%)",
            baseline_means["violation_rate_pct"],
            proposed_means["violation_rate_pct"],
            cmp["violation_rate_pct"]["difference_pp"],
            "pp difference",
        ),
        (
            "Mean PSM",
            baseline_means["mean_psm"],
            proposed_means["mean_psm"],
            cmp["mean_psm"]["difference"],
            "difference",
        ),
        (
            "Minimum PSM",
            baseline_means["min_psm"],
            proposed_means["min_psm"],
            cmp["min_psm"]["difference"],
            "difference",
        ),
    ]

    table = pd.DataFrame(
        {
            "Metric": [r[0] for r in rows],
            "Uniform Baseline": [_fmt(r[1]) for r in rows],
            "PSM-Adaptive": [_fmt(r[2]) for r in rows],
            "Difference": [_fmt(r[3]) for r in rows],
            "Difference Type": [r[4] for r in rows],
        }
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="psdt-section-heading">Primary Comparison Table</div>', unsafe_allow_html=True)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(
        "Values are means across all paired seeds run above; nothing here is hard-coded "
        "(Sprint 11 Deliverable 13). Reduction % = (Baseline - Proposed) / Baseline x 100. "
        "Estimated Energy is modeled/simulated energy, not a hardware power measurement."
    )

    success = evaluate_success_criterion(baseline_means, proposed_means)
    warnings_list = sanity_check(baseline_means, proposed_means)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="psdt-section-heading">Technical Success Criterion (Deliverable 21)</div>',
        unsafe_allow_html=True,
    )
    if success["success"]:
        st.success(
            f"Criterion met - energy reduced: {success['energy_reduced']}, messages reduced: "
            f"{success['messages_reduced']}, violation-rate difference: {success['violation_diff_pp']:.2f} pp "
            f"(tolerance {success['tolerance_pp']} pp)."
        )
    else:
        st.warning(
            f"Criterion NOT met - energy reduced: {success['energy_reduced']}, messages reduced: "
            f"{success['messages_reduced']}, violation-rate difference: {success['violation_diff_pp']:.2f} pp "
            f"(tolerance {success['tolerance_pp']} pp)."
        )

    if warnings_list:
        st.markdown(
            '<div class="psdt-section-heading">Sanity Checks (Deliverable 26)</div>', unsafe_allow_html=True
        )
        for w in warnings_list:
            st.warning(w)

    with st.expander("Per-seed raw metrics"):
        raw_table = pd.DataFrame(
            [
                {
                    "Seed": b["seed"],
                    "Experiment ID (Baseline)": b["experiment_id"],
                    "Experiment ID (Proposed)": p["experiment_id"],
                    "Sync Msgs (Base)": b["sync_messages"],
                    "Sync Msgs (Proposed)": p["sync_messages"],
                    "Energy J (Base)": round(b["estimated_energy_j"], 2),
                    "Energy J (Proposed)": round(p["estimated_energy_j"], 2),
                    "Violation % (Base)": round(b["violation_rate_pct"], 2),
                    "Violation % (Proposed)": round(p["violation_rate_pct"], 2),
                }
                for b, p in zip(baseline_runs, proposed_runs)
            ]
        )
        st.dataframe(raw_table, use_container_width=True, hide_index=True)
