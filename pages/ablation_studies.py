"""
Sprint 14 (Patent strengthening, Changes 3-5): Ablation Studies dashboard.

Runs and visualizes the three controlled experiments added in this
sprint on top of the existing Sprint 10/11 simulation and experiment
engines. This page does not duplicate the simulator or any DTCE/PEEE/
PSME/SCE/ARAC mathematics; it only orchestrates core/experiment_engine.py
and core/experiment_metrics.py.

- Change 3: resource-reduction vs perceptual-violation-rate trade-off
  curve across adaptation_level (Mild/Moderate/Aggressive).
- Change 4: four-way controlled ablation study (Method A "Uniform",
  Method B "PE-only adaptive", Method C "PT-only / non-stateful
  adaptive", Method D "Full PSM-Adaptive").
- Change 5: hysteresis ablation, comparing the full PSM-Adaptive method
  with vs without hysteresis/dwell-time persistence.
"""

import statistics

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.experiment_engine import (
    run_ablation_study,
    run_adaptation_sweep,
    run_hysteresis_ablation,
)
from core.experiment_metrics import aggregate_metric
from config.baseline_policies import (
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
from config.resource_profiles import ADAPTATION_LEVEL_OPTIONS

NODE_COUNT_OPTIONS = [10, 20, 30, 40, 50]

_METHOD_LABELS = {
    "uniform": "A: Uniform",
    "pe_only": "B: PE-only Adaptive",
    "pt_only": "C: PT-only / Non-stateful Adaptive",
    "adaptive": "D: Full PSM-Adaptive",
}
_METHOD_ORDER = ["uniform", "pe_only", "pt_only", "adaptive"]

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">Ablation Studies</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Controlled ablation experiments isolating which parts of the PSM-Adaptive control loop actually "
    "drive its resource savings and violation-rate behavior: a resource-vs-violation trade-off curve, a "
    "four-way method ablation, and a hysteresis on/off comparison. Every value below comes from a "
    "completed simulation run; nothing is hard-coded."
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
    num_seeds = st.selectbox("Seeds", seed_count_options, index=min(2, len(seed_count_options) - 1))
with c5:
    baseline_policy = st.selectbox(
        "Baseline Policy", UNIFORM_POLICY_OPTIONS, index=UNIFORM_POLICY_OPTIONS.index(DEFAULT_UNIFORM_POLICY)
    )

seeds = FULL_SEED_LIST[:num_seeds]

def _fmt(v, digits=2):
    return "-" if v is None else round(v, digits)


st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div class="psdt-section-heading">Change 4: Four-Way Controlled Ablation Study</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Runs Method A (Uniform), Method B (PE-only Adaptive, ignores the personalized Dynamic Perceptual "
    "Threshold), Method C (PT-only / Non-stateful Adaptive, no hysteresis or dwell-time persistence), and "
    "Method D (Full PSM-Adaptive, the frozen default) under identical seeds, node count, scenario, and "
    "duration, isolating each mechanism's individual contribution."
)
if st.button("Run Ablation Study", type="primary"):
    with st.spinner(f"Running {num_seeds} seed(s) x 4 methods ({num_seeds * 4} simulation runs)..."):
        st.session_state["abl_study_results"] = run_ablation_study(
            nodes=num_nodes, duration=duration_s, time_step=DEFAULT_TIME_STEP_S,
            scenario=scenario, seeds=seeds, baseline_policy=baseline_policy,
        )

abl_results = st.session_state.get("abl_study_results")
if abl_results:
    metric_keys = ["sync_messages", "estimated_energy_j", "violation_rate_pct",
                   "state_transitions", "resource_reallocations"]
    agg = {
        m: {k: aggregate_metric([r[k] for r in abl_results[m]])["mean"] for k in metric_keys}
        for m in _METHOD_ORDER
    }
    table = pd.DataFrame(
        {
            "Method": [_METHOD_LABELS[m] for m in _METHOD_ORDER],
            "Sync Messages": [_fmt(agg[m]["sync_messages"]) for m in _METHOD_ORDER],
            "Estimated Energy (J)": [_fmt(agg[m]["estimated_energy_j"]) for m in _METHOD_ORDER],
            "Violation Rate (%)": [_fmt(agg[m]["violation_rate_pct"], 3) for m in _METHOD_ORDER],
            "State Transitions": [_fmt(agg[m]["state_transitions"], 1) for m in _METHOD_ORDER],
            "Resource Reallocations": [_fmt(agg[m]["resource_reallocations"], 1) for m in _METHOD_ORDER],
        }
    )
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption(f"Means across {len(abl_results['uniform'])} seed(s) per method.")

    abl_fig = go.Figure()
    abl_fig.add_trace(go.Scatter(
        x=[agg[m]["violation_rate_pct"] for m in _METHOD_ORDER],
        y=[agg[m]["estimated_energy_j"] for m in _METHOD_ORDER],
        mode="markers+text", text=[_METHOD_LABELS[m].split(":")[0] for m in _METHOD_ORDER],
        textposition="top center", marker=dict(size=14, color=["#94A3B8", "#F59E0B", "#16A34A", "#0B3D91"]),
    ))
    abl_fig.update_layout(
        xaxis_title="Violation Rate (%)", yaxis_title="Estimated Energy (J)",
        height=380, margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(abl_fig, use_container_width=True)
    st.caption(
        "Each labeled point is one method's mean outcome across all seeds run above. Method D (Full "
        "PSM-Adaptive) is expected to sit furthest toward the lower-left (lower energy, lower violations) "
        "relative to the partial-mechanism methods B and C."
    )
else:
    st.info("Configure the experiment above and click **Run Ablation Study** to generate the comparison.")

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    '<div class="psdt-section-heading">Change 3: Resource-Reduction vs Violation-Rate Trade-off Curve</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Runs the Full PSM-Adaptive method (Method D) at each adaptation_level (Mild/Moderate/Aggressive "
    "resource-interval scaling) under identical seeds, node count, scenario, and duration, tracing how "
    "more aggressive resource reduction trades off against the perceptual-threshold violation rate."
)
if st.button("Run Adaptation Sweep", type="primary"):
    with st.spinner(f"Running {num_seeds} seed(s) x {len(ADAPTATION_LEVEL_OPTIONS)} adaptation level(s)..."):
        st.session_state["abl_sweep_results"] = run_adaptation_sweep(
            nodes=num_nodes, duration=duration_s, time_step=DEFAULT_TIME_STEP_S,
            scenario=scenario, seeds=seeds,
        )

sweep_results = st.session_state.get("abl_sweep_results")
if sweep_results:
    levels = list(sweep_results.keys())
    energy_means = [aggregate_metric([r["estimated_energy_j"] for r in sweep_results[lvl]])["mean"] for lvl in levels]
    viol_means = [aggregate_metric([r["violation_rate_pct"] for r in sweep_results[lvl]])["mean"] for lvl in levels]
    sync_means = [aggregate_metric([r["sync_messages"] for r in sweep_results[lvl]])["mean"] for lvl in levels]

    sweep_table = pd.DataFrame(
        {
            "Adaptation Level": levels,
            "Sync Messages": [_fmt(v) for v in sync_means],
            "Estimated Energy (J)": [_fmt(v) for v in energy_means],
            "Violation Rate (%)": [_fmt(v, 3) for v in viol_means],
        }
    )
    st.dataframe(sweep_table, use_container_width=True, hide_index=True)

    sweep_fig = go.Figure()
    sweep_fig.add_trace(go.Scatter(
        x=viol_means, y=energy_means, mode="lines+markers+text", text=levels,
        textposition="top center", marker=dict(size=13, color="#0B3D91"), line=dict(color="#0B3D91"),
    ))
    sweep_fig.update_layout(
        xaxis_title="Violation Rate (%)", yaxis_title="Estimated Energy (J)",
        height=380, margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(sweep_fig, use_container_width=True)
    st.caption(
        f"Means across {len(sweep_results[levels[0]])} seed(s) per level. Moving from Mild to Aggressive "
        "is expected to reduce estimated energy at the cost of a higher violation rate, tracing out the "
        "trade-off curve rather than a single fixed operating point."
    )
else:
    st.info("Click **Run Adaptation Sweep** to generate the trade-off curve above.")

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    '<div class="psdt-section-heading">Change 5: Hysteresis Ablation</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Runs the Full PSM-Adaptive method both with hysteresis (the frozen default) and without hysteresis "
    "(Method C, immediate reaction with no dwell-time persistence or boundary margin) under identical "
    "seeds, node count, scenario, and duration, to quantify hysteresis's effect on state-transition churn, "
    "resource reallocations, synchronization messages, energy, and the violation rate."
)
if st.button("Run Hysteresis Ablation", type="primary"):
    with st.spinner(f"Running {num_seeds} seed(s) x 2 configurations (with/without hysteresis)..."):
        st.session_state["abl_hyst_results"] = run_hysteresis_ablation(
            nodes=num_nodes, duration=duration_s, time_step=DEFAULT_TIME_STEP_S,
            scenario=scenario, seeds=seeds, baseline_policy=baseline_policy,
        )

hyst_results = st.session_state.get("abl_hyst_results")
if hyst_results:
    without_runs = hyst_results["without_hysteresis"]
    with_runs = hyst_results["with_hysteresis"]
    hyst_metric_keys = ["state_transitions", "resource_reallocations", "sync_messages",
                         "estimated_energy_j", "violation_rate_pct"]
    without_agg = {k: aggregate_metric([r[k] for r in without_runs])["mean"] for k in hyst_metric_keys}
    with_agg = {k: aggregate_metric([r[k] for r in with_runs])["mean"] for k in hyst_metric_keys}

    hyst_rows = [
        ("State Transitions", without_agg["state_transitions"], with_agg["state_transitions"]),
        ("Resource Reallocations", without_agg["resource_reallocations"], with_agg["resource_reallocations"]),
        ("Sync Messages", without_agg["sync_messages"], with_agg["sync_messages"]),
        ("Estimated Energy (J)", without_agg["estimated_energy_j"], with_agg["estimated_energy_j"]),
        ("Violation Rate (%)", without_agg["violation_rate_pct"], with_agg["violation_rate_pct"]),
    ]
    hyst_table = pd.DataFrame(
        {
            "Metric": [r[0] for r in hyst_rows],
            "Without Hysteresis": [_fmt(r[1], 3) for r in hyst_rows],
            "With Hysteresis": [_fmt(r[2], 3) for r in hyst_rows],
        }
    )
    st.dataframe(hyst_table, use_container_width=True, hide_index=True)
    st.caption(f"Means across {len(without_runs)} seed(s) per configuration.")

    hyst_fig = go.Figure()
    hyst_fig.add_trace(go.Bar(
        name="Without Hysteresis",
        x=["State Transitions", "Resource Reallocations"],
        y=[without_agg["state_transitions"], without_agg["resource_reallocations"]],
        marker_color="#94A3B8",
    ))
    hyst_fig.add_trace(go.Bar(
        name="With Hysteresis",
        x=["State Transitions", "Resource Reallocations"],
        y=[with_agg["state_transitions"], with_agg["resource_reallocations"]],
        marker_color="#0B3D91",
    ))
    hyst_fig.update_layout(
        barmode="group", height=360, margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(hyst_fig, use_container_width=True)
    st.caption(
        "Hysteresis and dwell-time persistence are expected to reduce state-transition and "
        "resource-reallocation churn substantially, at little or no cost in violation rate."
    )
else:
    st.info("Click **Run Hysteresis Ablation** to generate the comparison above.")
