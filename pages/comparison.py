import statistics

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.experiment_engine import (
    run_seed_matrix,
    run_scenario_matrix,
    run_body_zone_experiment,
    run_disturbance_experiment,
    ControlledExperiment,
)
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
_SCENARIO_SHORT = {s: s.split(":")[0].replace("Scenario ", "") for s in SCENARIO_OPTIONS}

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

seeds = FULL_SEED_LIST[:num_seeds]

run_clicked = st.button("Run Controlled Experiment", type="primary")

if run_clicked:
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
        "comparison table and charts. No results are hard-coded here; every value comes from a "
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
    baseline_agg = {k: aggregate_metric([r[k] for r in baseline_runs]) for k in metric_keys}
    proposed_agg = {k: aggregate_metric([r[k] for r in proposed_runs]) for k in metric_keys}
    baseline_means = {k: baseline_agg[k]["mean"] for k in metric_keys}
    proposed_means = {k: proposed_agg[k]["mean"] for k in metric_keys}
    cmp = compare_runs(baseline_means, proposed_means)

    def _fmt(v, digits=2):
        return "-" if v is None else round(v, digits)

    rows = [
        ("Sync Messages (mean per run)", baseline_means["sync_messages"], proposed_means["sync_messages"],
         cmp["sync_messages"]["reduction_pct"], "% reduction"),
        ("Radio-Active Time (s, mean per run)", baseline_means["radio_active_time_s"],
         proposed_means["radio_active_time_s"], cmp["radio_active_time_s"]["reduction_pct"], "% reduction"),
        ("Estimated Energy (J, mean per run)", baseline_means["estimated_energy_j"],
         proposed_means["estimated_energy_j"], cmp["estimated_energy_j"]["reduction_pct"], "% reduction"),
        ("Violation Rate (%)", baseline_means["violation_rate_pct"], proposed_means["violation_rate_pct"],
         cmp["violation_rate_pct"]["difference_pp"], "pp difference"),
        ("Mean PSM", baseline_means["mean_psm"], proposed_means["mean_psm"],
         cmp["mean_psm"]["difference"], "difference"),
        ("Minimum PSM", baseline_means["min_psm"], proposed_means["min_psm"],
         cmp["min_psm"]["difference"], "difference"),
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

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="psdt-section-heading">Trade-Off: Resource Use vs Perceptual Violations (Deliverable 14)</div>',
        unsafe_allow_html=True,
    )
    trade_fig = go.Figure()
    trade_fig.add_trace(go.Scatter(
        x=[r["violation_rate_pct"] for r in baseline_runs],
        y=[r["estimated_energy_j"] for r in baseline_runs],
        mode="markers", name="Uniform Baseline",
        marker=dict(size=11, color="#94A3B8"),
        text=[f'seed {r["seed"]}' for r in baseline_runs],
    ))
    trade_fig.add_trace(go.Scatter(
        x=[r["violation_rate_pct"] for r in proposed_runs],
        y=[r["estimated_energy_j"] for r in proposed_runs],
        mode="markers", name="PSM-Adaptive",
        marker=dict(size=11, color="#0B3D91"),
        text=[f'seed {r["seed"]}' for r in proposed_runs],
    ))
    trade_fig.update_layout(
        xaxis_title="Perceptual-Threshold Violation Rate (%)",
        yaxis_title="Estimated Energy (J)",
        height=380, margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(trade_fig, use_container_width=True)
    st.caption(
        "Each point is one paired seed run. The ideal outcome is Proposed points lower (less energy) "
        "without shifting right (more violations) relative to Baseline points."
    )

    with st.expander("Statistical summary (Deliverable 20)"):
        stat_rows = []
        for k in ["sync_messages", "radio_active_time_s", "estimated_energy_j", "violation_rate_pct", "mean_psm"]:
            for label, agg in (("Uniform Baseline", baseline_agg[k]), ("PSM-Adaptive", proposed_agg[k])):
                stat_rows.append({
                    "Metric": k, "Strategy": label,
                    "Mean": _fmt(agg["mean"]), "Median": _fmt(agg["median"]),
                    "Stdev": _fmt(agg["stdev"]), "Min": _fmt(agg["min"]), "Max": _fmt(agg["max"]),
                    "n": agg["n"],
                })
        st.dataframe(pd.DataFrame(stat_rows), use_container_width=True, hide_index=True)

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

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="psdt-section-heading">Per-Scenario Comparison (Deliverables 7, 15-17)</div>', unsafe_allow_html=True)
st.caption(
    "Runs the same paired Uniform vs PSM-Adaptive comparison across all three scenarios "
    "(Stable / Moderate / Challenging) using the Nodes, Seeds, and Baseline Policy configured above."
)
scenario_clicked = st.button("Run Scenario Comparison")

if scenario_clicked:
    with st.spinner(f"Running {num_seeds} seed(s) x 3 scenarios x 2 strategies..."):
        st.session_state["exp11_scenario_results"] = run_scenario_matrix(
            nodes=num_nodes, duration=duration_s, time_step=DEFAULT_TIME_STEP_S,
            seeds=seeds, baseline_policy=baseline_policy,
        )
    st.session_state["exp11_scenario_config"] = {
        "nodes": num_nodes, "duration_s": duration_s, "seeds": seeds, "baseline_policy": baseline_policy,
    }

scenario_results = st.session_state.get("exp11_scenario_results")
if scenario_results:
    scen_labels = [_SCENARIO_SHORT[s] for s in SCENARIO_OPTIONS]
    sync_base, sync_prop = [], []
    energy_base, energy_prop, energy_base_sd, energy_prop_sd = [], [], [], []
    viol_base, viol_prop = [], []
    for s in SCENARIO_OPTIONS:
        b_runs = scenario_results[s]["baseline"]
        p_runs = scenario_results[s]["proposed"]
        sync_base.append(statistics.fmean([r["sync_messages"] for r in b_runs]))
        sync_prop.append(statistics.fmean([r["sync_messages"] for r in p_runs]))
        e_b = [r["estimated_energy_j"] for r in b_runs]
        e_p = [r["estimated_energy_j"] for r in p_runs]
        energy_base.append(statistics.fmean(e_b))
        energy_prop.append(statistics.fmean(e_p))
        energy_base_sd.append(statistics.pstdev(e_b) if len(e_b) > 1 else 0.0)
        energy_prop_sd.append(statistics.pstdev(e_p) if len(e_p) > 1 else 0.0)
        viol_base.append(statistics.fmean([r["violation_rate_pct"] for r in b_runs]))
        viol_prop.append(statistics.fmean([r["violation_rate_pct"] for r in p_runs]))

    st.markdown("**Sync Messages by Scenario (Deliverable 15)**")
    st.bar_chart(pd.DataFrame({"Uniform Baseline": sync_base, "PSM-Adaptive": sync_prop}, index=scen_labels), stack=False)

    st.markdown("**Estimated Energy by Scenario, with variability (Deliverable 16)**")
    energy_fig = go.Figure()
    energy_fig.add_trace(go.Bar(
        name="Uniform Baseline", x=scen_labels, y=energy_base,
        error_y=dict(type="data", array=energy_base_sd), marker_color="#94A3B8",
    ))
    energy_fig.add_trace(go.Bar(
        name="PSM-Adaptive", x=scen_labels, y=energy_prop,
        error_y=dict(type="data", array=energy_prop_sd), marker_color="#0B3D91",
    ))
    energy_fig.update_layout(
        barmode="group", yaxis_title="Estimated Energy (J)", height=360,
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(energy_fig, use_container_width=True)
    st.caption(f"Error bars show +/- 1 population stdev across {len(seeds)} paired seed(s) per scenario.")

    st.markdown("**Violation Rate by Scenario (Deliverable 17)**")
    st.bar_chart(pd.DataFrame({"Uniform Baseline": viol_base, "PSM-Adaptive": viol_prop}, index=scen_labels), stack=False)
    st.caption(
        "Energy reduction alone is insufficient; violation rate should not materially worsen "
        "for the Proposed method relative to Baseline."
    )
else:
    st.info("Click **Run Scenario Comparison** to generate the per-scenario charts above.")

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="psdt-section-heading">Body-Zone Analysis (Deliverables 11, 18)</div>', unsafe_allow_html=True)
st.caption(
    "Compares mean synchronization interval by body zone for one paired run (first configured seed), "
    "using the Nodes, Scenario, and Baseline Policy configured above."
)
zone_clicked = st.button("Run Body-Zone Analysis")

if zone_clicked:
    with st.spinner("Running one paired simulation for body-zone analysis..."):
        zone_exp = ControlledExperiment(
            seed=seeds[0], nodes=num_nodes, duration=duration_s, time_step=DEFAULT_TIME_STEP_S,
            scenario=scenario, baseline_policy=baseline_policy,
        )
        zb, zp = zone_exp.run_pair()
        st.session_state["exp11_zone_results"] = run_body_zone_experiment(zb, zp)

zone_results = st.session_state.get("exp11_zone_results")
if zone_results:
    zones = list(zone_results["baseline"].keys())
    zone_df = pd.DataFrame(
        {
            "Uniform Baseline": [zone_results["baseline"][z]["mean_sync_interval_ms"] for z in zones],
            "PSM-Adaptive": [zone_results["proposed"][z]["mean_sync_interval_ms"] for z in zones],
        },
        index=zones,
    )
    st.markdown("**Mean Sync Interval by Body Zone**")
    st.bar_chart(zone_df, stack=False)
    st.caption(
        "Uniform Baseline should appear flat across zones (genuinely uniform, Deliverable 3). "
        "PSM-Adaptive should vary by zone if body-zone-specific perceptual differentiation is "
        "actually driving resource allocation (Deliverable 11)."
    )
else:
    st.info("Click **Run Body-Zone Analysis** to generate the chart above.")

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="psdt-section-heading">Disturbance &amp; Recovery Response (Deliverables 8, 19)</div>', unsafe_allow_html=True)
st.caption(
    "Injects an identically-timed network-jitter and clock-drift disturbance into both a Baseline "
    "and a Proposed run (first configured seed) and compares each method's PT/PE/PSM response and "
    "recovery time. Recovery = non-negative PSM sustained for the same persistence window for both methods."
)
disturbance_clicked = st.button("Run Disturbance Experiment")

if disturbance_clicked:
    with st.spinner("Running paired disturbance simulation..."):
        st.session_state["exp11_disturbance_results"] = run_disturbance_experiment(
            seed=seeds[0], nodes=num_nodes, duration=duration_s, time_step=DEFAULT_TIME_STEP_S,
            scenario=scenario, baseline_policy=baseline_policy,
        )

dist_results = st.session_state.get("exp11_disturbance_results")
if dist_results:
    start_t = dist_results["disturbance_start_s"]
    end_t = dist_results["disturbance_end_s"]
    base_engine = dist_results["baseline_engine"]
    prop_engine = dist_results["proposed_engine"]

    r1, r2 = st.columns(2)
    r1.metric("Baseline recovery time (s)", dist_results["baseline_recovery_s"])
    r2.metric("Proposed recovery time (s)", dist_results["proposed_recovery_s"])

    def _response_fig(engine, title):
        g = engine.history.global_dataframe_dict()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=g["timestamp"], y=g["mean_pt"], name="Mean PT", line=dict(color="#94A3B8")))
        fig.add_trace(go.Scatter(x=g["timestamp"], y=g["mean_pe"], name="Mean PE", line=dict(color="#F59E0B")))
        fig.add_trace(go.Scatter(x=g["timestamp"], y=g["mean_psm"], name="Mean PSM", line=dict(color="#0B3D91")))
        fig.add_vline(x=start_t, line_dash="dash", line_color="#DC2626")
        fig.add_vline(x=end_t, line_dash="dash", line_color="#16A34A")
        fig.update_layout(
            title=title, height=340, margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        return fig

    d1, d2 = st.columns(2)
    with d1:
        st.plotly_chart(_response_fig(base_engine, "Uniform Baseline"), use_container_width=True)
    with d2:
        st.plotly_chart(_response_fig(prop_engine, "PSM-Adaptive"), use_container_width=True)

    rep_node_id = next(iter(base_engine.coordinator.registry.keys()))
    base_node_series = base_engine.history.node_series[rep_node_id]
    prop_node_series = prop_engine.history.node_series[rep_node_id]
    sync_fig = go.Figure()
    sync_fig.add_trace(go.Scatter(
        x=base_node_series["timestamp"], y=base_node_series["sync_interval_ms"],
        name="Uniform Baseline", line=dict(color="#94A3B8"),
    ))
    sync_fig.add_trace(go.Scatter(
        x=prop_node_series["timestamp"], y=prop_node_series["sync_interval_ms"],
        name="PSM-Adaptive", line=dict(color="#0B3D91"),
    ))
    sync_fig.add_vline(x=start_t, line_dash="dash", line_color="#DC2626")
    sync_fig.add_vline(x=end_t, line_dash="dash", line_color="#16A34A")
    sync_fig.update_layout(
        title=f"Synchronization Interval Over Time (representative node {rep_node_id})",
        yaxis_title="Sync Interval (ms)", height=340, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(sync_fig, use_container_width=True)
    st.caption(
        "Red dashed line: disturbance injected. Green dashed line: disturbance ends. "
        "The Proposed method is expected to tighten synchronization (lower interval) during/after "
        "the disturbance rather than simply always using fewer resources."
    )
else:
    st.info("Click **Run Disturbance Experiment** to generate the response plots above.")
