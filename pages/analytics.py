import streamlit as st

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">Analytics</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

cards = [
    ("📦", "Packets"),
    ("🔋", "Battery"),
    ("⚡", "Energy"),
    ("📡", "Communication"),
    ("🧭", "Node States"),
]

cols = st.columns(len(cards))
for col, (icon, label) in zip(cols, cards):
    with col:
        st.markdown(
            f"""
            <div class="psdt-placeholder-box">
            <div style="font-size:1.8rem;">{icon}</div>
            <div style="font-weight:700; color:#0B3D91; margin-top:0.4rem;">{label}</div>
            <div style="font-size:0.85rem; margin-top:0.5rem;">No data yet</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------
# Sprint 5: first real experimental visualization - Dynamic Perceptual
# Threshold by Body Zone, computed by the DTCE for every active node.
# ---------------------------------------------------------------------
import pandas as pd
import altair as alt
from core.constants import ZONE_ORDER
from core.sce import STATE_ORDER as SCE_STATE_ORDER
from config.resource_profiles import (
    ENERGY_COST_PER_ACTIVE_SECOND_BY_LEVEL,
    FIXED_BASELINE_TRANSMIT_POWER_LEVEL,
)

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Dynamic Perceptual Threshold by Body Zone")

coordinator = st.session_state.get("dt_coordinator")
if coordinator and coordinator.dtce_audit:
    pt_rows = [
        {"Body Zone": audit.body_zone, "Dynamic PT (ms)": audit.dynamic_pt_ms}
        for audit in coordinator.dtce_audit.values()
    ]
    pt_df = pd.DataFrame(pt_rows)

    mean_pt_by_zone = (
        pt_df.groupby("Body Zone")["Dynamic PT (ms)"]
        .mean()
        .reindex([z for z in ZONE_ORDER if z in pt_df["Body Zone"].unique()])
    )
    st.bar_chart(mean_pt_by_zone)
    st.caption(
        "Mean Dynamic Perceptual Threshold PTz(t) per body zone, across all active "
        "nodes in the current digital twin. Computed by the DTCE (Sprint 5); values "
        "change with frequency, actuator type, calibration, motion, and environment."
    )
else:
    st.markdown(
        '<div class="psdt-placeholder-box">Initialize the Digital Twin and run a '
        'communication cycle on the Simulation page to populate this chart.</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# Sprint 6: Perceived Error analytics, computed by the PEEE for every
# active node. PE is an ESTIMATED PERCEIVED SYNCHRONIZATION ERROR derived
# from residual/differential timing contributions - not a claim about
# absolute end-to-end latency, and not the same quantity as PT.
# ---------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Mean Perceived Error by Body Zone")

if coordinator and coordinator.peee_audit:
    pe_rows = [
        {
            "Body Zone": audit.body_zone,
            "Perceived Error (ms)": audit.perceived_error_ms,
            "CD (ms)": audit.contribution_cd,
            "ND (ms)": audit.contribution_nd,
            "AD (ms)": audit.contribution_ad,
            "MD (ms)": audit.contribution_md,
        }
        for audit in coordinator.peee_audit.values()
    ]
    pe_df = pd.DataFrame(pe_rows)

    mean_pe_by_zone = (
        pe_df.groupby("Body Zone")["Perceived Error (ms)"]
        .mean()
        .reindex([z for z in ZONE_ORDER if z in pe_df["Body Zone"].unique()])
    )
    st.bar_chart(mean_pe_by_zone)
    st.caption(
        "Mean Estimated Perceived Error PEz(t) per body zone, across all active "
        "nodes in the current digital twin. Computed by the PEEE (Sprint 6) from "
        "residual clock drift, network, actuator driver, and mechanical startup "
        "contributions."
    )

    st.markdown("###### Average PE Components")
    component_means = pe_df[["CD (ms)", "ND (ms)", "AD (ms)", "MD (ms)"]].mean()
    component_means.index = ["CD", "ND", "AD", "MD"]
    st.bar_chart(component_means)
    st.caption(
        "Average contribution of each residual timing component to the estimated "
        "Perceived Error, across all active nodes. This shows which contributor is "
        "currently dominating synchronization error under the selected PE model "
        "and weights; it is not a safety or severity classification."
    )

    st.markdown("###### Threshold–Error Diagnostic View")
    if coordinator.dtce_audit:
        pt_by_zone = (
            pd.DataFrame(
                {"Body Zone": a.body_zone, "PT (ms)": a.dynamic_pt_ms}
                for a in coordinator.dtce_audit.values()
            )
            .groupby("Body Zone")["PT (ms)"]
            .mean()
        )
        pe_by_zone = (
            pd.DataFrame(
                {"Body Zone": a.body_zone, "PE (ms)": a.perceived_error_ms}
                for a in coordinator.peee_audit.values()
            )
            .groupby("Body Zone")["PE (ms)"]
            .mean()
        )
        diagnostic_df = pd.concat([pt_by_zone, pe_by_zone], axis=1).reindex(
            [z for z in ZONE_ORDER if z in pt_by_zone.index]
        )
        diagnostic_long = diagnostic_df.reset_index().melt(
            id_vars="Body Zone",
            value_vars=["PT (ms)", "PE (ms)"],
            var_name="Metric",
            value_name="Milliseconds",
        )
        diagnostic_chart = (
            alt.Chart(diagnostic_long)
            .mark_bar()
            .encode(
                x=alt.X("Metric:N", title=None, axis=alt.Axis(labels=False, ticks=False)),
                y=alt.Y("Milliseconds:Q"),
                color=alt.Color(
                    "Metric:N",
                    scale=alt.Scale(range=["#1D4ED8", "#93C5FD"]),
                    legend=alt.Legend(title=None),
                ),
                column=alt.Column("Body Zone:N", title=None),
                tooltip=["Body Zone", "Metric", "Milliseconds"],
            )
            .properties(width=70)
        )
        st.altair_chart(diagnostic_chart, use_container_width=False)
        st.caption(
            "Side-by-side comparison of mean Dynamic Perceptual Threshold PTz(t) and "
            "mean Estimated Perceived Error PEz(t) per body zone. This is a diagnostic "
            "preview only - PT and PE are not yet combined into a Perceptual "
            "Synchronization Margin, and no zone or node is labeled safe or critical "
            "here. That interpretation belongs to PSME/SCE (Sprint 7+)."
        )
    else:
        st.markdown(
            '<div class="psdt-placeholder-box">Run a communication cycle to populate '
            'the Threshold–Error Diagnostic View.</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="psdt-placeholder-box">Initialize the Digital Twin and run a '
        'communication cycle on the Simulation page to populate Perceived Error '
        'analytics.</div>',
        unsafe_allow_html=True,
    )
# ---------------------------------------------------------------------
# Sprint 7: Perceptual Synchronization Margin analytics, computed by the
# PSME for every node that already has both PT (DTCE) and PE (PEEE).
# ---------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Mean Perceptual Synchronization Margin by Body Zone")
if coordinator and coordinator.psme_audit:
    psm_rows = [
        {"Body Zone": node.body_zone, "PSM (ms)": node.psm}
        for node in coordinator.registry.values()
        if node.psm is not None
    ]
    psm_df = pd.DataFrame(psm_rows)
    mean_psm_by_zone = (
        psm_df.groupby("Body Zone")["PSM (ms)"]
        .mean()
        .reindex([z for z in ZONE_ORDER if z in psm_df["Body Zone"].unique()])
    )
    st.bar_chart(mean_psm_by_zone)
    st.caption(
        "Mean Perceptual Synchronization Margin PSMz(t) per body zone, across all "
        "active nodes. Computed by the PSME (Sprint 7) as PSM = PT - PE; positive "
        "values indicate margin remaining before the perceptual threshold is "
        "exceeded, negative values indicate the threshold has been exceeded."
    )
    st.markdown("###### PT–PE–PSM Diagnostic View")
    ptpe_psm_rows = [
        {
            "Body Zone": node.body_zone,
            "PT (ms)": node.perceptual_threshold,
            "PE (ms)": node.perceived_error,
            "PSM (ms)": node.psm,
        }
        for node in coordinator.registry.values()
        if node.psm is not None
    ]
    ptpe_psm_df = pd.DataFrame(ptpe_psm_rows)
    diagnostic_by_zone = (
        ptpe_psm_df.groupby("Body Zone")[["PT (ms)", "PE (ms)", "PSM (ms)"]]
        .mean()
        .reindex([z for z in ZONE_ORDER if z in ptpe_psm_df["Body Zone"].unique()])
    )
    st.dataframe(diagnostic_by_zone.round(2), use_container_width=True)
    st.caption(
        "Mean PT, PE and resulting PSM per body zone. PSM = PT - PE: remaining "
        "margin when positive, exceeded margin when negative."
    )
    st.markdown("###### PSM Distribution")
    psm_hist = (
        alt.Chart(psm_df)
        .mark_bar()
        .encode(
            x=alt.X("PSM (ms):Q", bin=alt.Bin(maxbins=20), title="PSM (ms)"),
            y=alt.Y("count()", title="Node Count"),
        )
    )
    st.altair_chart(psm_hist, use_container_width=True)
    st.caption(
        "Distribution of Perceptual Synchronization Margin values across all "
        "active nodes. Values below zero (Margin Sign: NEGATIVE) indicate the "
        "node's perceptual threshold has been exceeded by the estimated "
        "perceived error."
    )
    st.markdown("###### PT–PE–PSM Decomposition (per node)")
    decomp_rows = []
    for node in coordinator.registry.values():
        if node.psm is None:
            continue
        pt = node.perceptual_threshold
        pe = node.perceived_error
        psm = node.psm
        decomp_rows.append({
            "Node": node.node_id,
            "PT (ms)": pt,
            "PE (ms)": pe,
            "PSM (ms)": psm,
            "PE Consumed": min(pe, pt),
            "Remaining PSM": max(psm, 0.0),
            "Exceeded": max(-psm, 0.0),
        })
    decomp_df = pd.DataFrame(decomp_rows).sort_values("PSM (ms)")
    decomp_long = decomp_df.melt(
        id_vars=["Node", "PT (ms)", "PE (ms)", "PSM (ms)"],
        value_vars=["PE Consumed", "Remaining PSM", "Exceeded"],
        var_name="Segment",
        value_name="Milliseconds",
    )
    decomp_chart = (
        alt.Chart(decomp_long)
        .mark_bar()
        .encode(
            x=alt.X("Node:N", sort=list(decomp_df["Node"]), title="Node (sorted by PSM, ascending)"),
            y=alt.Y("Milliseconds:Q", stack="zero", title="Milliseconds"),
            color=alt.Color(
                "Segment:N",
                scale=alt.Scale(
                    domain=["PE Consumed", "Remaining PSM", "Exceeded"],
                    range=["#3B82F6", "#16A34A", "#DC2626"],
                ),
            ),
            tooltip=["Node", "PT (ms)", "PE (ms)", "PSM (ms)", "Segment", "Milliseconds"],
        )
    )
    st.altair_chart(decomp_chart, use_container_width=True)
    st.caption(
        "Per-node PT budget decomposition: blue is the perceived error consumed "
        "against the threshold, green is the remaining PSM budget, and red (when "
        "present) is the amount by which PE exceeds PT. Nodes are ordered by PSM "
        "ascending so the smallest margins appear first; no synchronization state "
        "is assigned here."
    )

    st.markdown("###### PSM Audit Table")
    audit_table_rows = [
        {
            "Node": node.node_id,
            "Zone": node.body_zone,
            "PT (ms)": round(node.perceptual_threshold, 2),
            "PE (ms)": round(node.perceived_error, 2),
            "PSM (ms)": round(node.psm, 2),
            "NPSM": round(node.normalized_psm, 4),
            "Threshold Utilization (%)": round(node.threshold_utilization_pct, 2),
            "Margin Sign": node.margin_sign,
            "State": node.sync_state,
            "Previous State": node.previous_state,
            "Transition": node.transition_flag,
            "Persistence": node.persistence_counter,
        }
        for node in coordinator.registry.values()
        if node.psm is not None
    ]
    audit_table_df = pd.DataFrame(audit_table_rows)
    sort_ascending = st.checkbox(
        "Sort ascending (smallest PSM first)", value=True, key="psm_audit_sort_asc"
    )
    audit_table_df = audit_table_df.sort_values("PSM (ms)", ascending=sort_ascending)
    st.dataframe(audit_table_df, hide_index=True, use_container_width=True)
    st.caption(
        "Full per-node PSM audit trail (Node, Zone, PT, PE, PSM, NPSM, Threshold "
        "Utilization, Margin Sign, State, Previous State, Transition, Persistence), "
        "sortable by any column (click a column header) to surface the nodes with "
        "the smallest remaining margin first. State/Previous State/Transition/"
        "Persistence are produced by the SCE (Sprint 8) from NPSM, with hysteresis "
        "and dwell-time persistence preventing rapid oscillation near a boundary."
    )
else:
    st.markdown(
        '<div class="psdt-placeholder-box">Run a communication cycle on the '
        'Simulation page to populate Perceptual Synchronization Margin '
        'analytics.</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------
# Sprint 8: Synchronization Classification Engine (SCE) analytics. State
# values are read directly from each node's sync_state/state_history -
# never re-derived here. Classification itself lives in core/sce.py.
# ---------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Synchronization State Analytics")

if coordinator and coordinator.sce_audit:
    classified_nodes = [n for n in coordinator.registry.values() if n.sync_state != "Unclassified"]

    st.markdown("###### Current State Distribution")
    state_counts_rows = [
        {"State": s, "Node Count": sum(1 for n in classified_nodes if n.sync_state == s)}
        for s in SCE_STATE_ORDER
    ]
    state_counts_df = pd.DataFrame(state_counts_rows)
    state_dist_chart = (
        alt.Chart(state_counts_df)
        .mark_bar()
        .encode(
            x=alt.X("Node Count:Q"),
            y=alt.Y("State:N", sort=SCE_STATE_ORDER),
            color=alt.Color(
                "State:N",
                scale=alt.Scale(
                    domain=SCE_STATE_ORDER,
                    range=["#DC2626", "#F59E0B", "#3B82F6", "#16A34A"],
                ),
                legend=None,
            ),
            tooltip=["State", "Node Count"],
        )
    )
    st.altair_chart(state_dist_chart, use_container_width=True)
    st.caption(
        "Count of active nodes currently classified into each of the four "
        "locked synchronization states (IMMEDIATE, ELEVATED, NOMINAL, RELAXED) "
        "by the SCE."
    )

    st.markdown("###### State Distribution by Body Zone")
    zone_state_rows = [
        {"Body Zone": zone, "State": s,
         "Node Count": sum(1 for n in classified_nodes if n.body_zone == zone and n.sync_state == s)}
        for zone in ZONE_ORDER
        for s in SCE_STATE_ORDER
    ]
    zone_state_df = pd.DataFrame(zone_state_rows)
    zone_state_chart = (
        alt.Chart(zone_state_df)
        .mark_bar()
        .encode(
            x=alt.X("Body Zone:N", sort=ZONE_ORDER),
            y=alt.Y("Node Count:Q"),
            color=alt.Color(
                "State:N",
                scale=alt.Scale(
                    domain=SCE_STATE_ORDER,
                    range=["#DC2626", "#F59E0B", "#3B82F6", "#16A34A"],
                ),
            ),
            tooltip=["Body Zone", "State", "Node Count"],
        )
    )
    st.altair_chart(zone_state_chart, use_container_width=True)
    st.caption(
        "Synchronization state breakdown per body zone, so a zone with a "
        "disproportionate share of ELEVATED/IMMEDIATE nodes stands out."
    )

    st.markdown("###### State Timeline (selected node)")
    timeline_candidates = [n.node_id for n in coordinator.registry.values() if n.state_history]
    if timeline_candidates:
        timeline_node_id = st.selectbox("Select node for state timeline", timeline_candidates)
        timeline_node = coordinator.registry[timeline_node_id]
        timeline_df = pd.DataFrame(timeline_node.state_history)
        timeline_chart = (
            alt.Chart(timeline_df)
            .mark_line(point=True, interpolate="step-after")
            .encode(
                x=alt.X("step:Q", title="Simulation Cycle"),
                y=alt.Y("state:N", sort=SCE_STATE_ORDER, title="State"),
                tooltip=["step", "timestamp", "state"],
            )
        )
        st.altair_chart(timeline_chart, use_container_width=True)
        st.caption(
            f"Synchronization state evolution for {timeline_node_id} over its "
            "rolling state_history buffer (most recent cycles)."
        )
    else:
        st.markdown(
            '<div class="psdt-placeholder-box">Run more communication cycles to build up state history.</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="psdt-placeholder-box">Run a communication cycle on the '
        'Simulation page to populate Synchronization State analytics.</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# Sprint 9: Resource Allocation Analytics (ARAC) - Deliverables 13, 15,
# 16, 17, 18.
# ---------------------------------------------------------------------
st.subheader("Resource Allocation Analytics")

if coordinator and coordinator.arac_audit:
    adaptive_nodes = [n for n in coordinator.registry.values() if n.resource_status == "Adaptive"]

    st.markdown("###### Average Resource Allocation")
    avg_sync = sum(n.allocated_sync_interval_ms for n in adaptive_nodes) / len(adaptive_nodes)
    avg_beacon = sum(n.allocated_beacon_interval_ms for n in adaptive_nodes) / len(adaptive_nodes)
    avg_wakeup = sum(n.allocated_radio_wakeup_interval_ms for n in adaptive_nodes) / len(adaptive_nodes)
    avg_power = sum(n.allocated_transmit_power_pct for n in adaptive_nodes) / len(adaptive_nodes)
    avg_cols = st.columns(4)
    avg_cols[0].metric("Avg Sync Interval", f"{avg_sync:.0f} ms")
    avg_cols[1].metric("Avg Beacon Frequency", f"{avg_beacon:.0f} ms")
    avg_cols[2].metric("Avg Transmit Power", f"{avg_power:.0f} %")
    avg_cols[3].metric("Avg Wake-up Time", f"{avg_wakeup:.0f} ms")

    st.markdown("###### Body Zone Resource Allocation")
    zone_avg_rows = [
        {
            "Body Zone": zone,
            "Avg Sync Interval (ms)": sum(
                n.allocated_sync_interval_ms for n in adaptive_nodes if n.body_zone == zone
            ) / max(1, sum(1 for n in adaptive_nodes if n.body_zone == zone)),
        }
        for zone in ZONE_ORDER
        if any(n.body_zone == zone for n in adaptive_nodes)
    ]
    if zone_avg_rows:
        zone_avg_df = pd.DataFrame(zone_avg_rows)
        zone_avg_chart = (
            alt.Chart(zone_avg_df)
            .mark_bar()
            .encode(
                x=alt.X("Avg Sync Interval (ms):Q"),
                y=alt.Y("Body Zone:N", sort=ZONE_ORDER),
                tooltip=["Body Zone", "Avg Sync Interval (ms)"],
            )
        )
        st.altair_chart(zone_avg_chart, use_container_width=True)
        st.caption(
            "Average ARAC-allocated synchronization interval per body zone, "
            "demonstrating differentiated resource allocation across anatomical "
            "regions (Sprint 9 Deliverable 17)."
        )

    st.markdown("###### Resource Parameter Timeline")
    timeline_node_id = st.selectbox(
        "Select node for resource timeline",
        [n.node_id for n in adaptive_nodes],
        key="resource_timeline_node",
    )
    timeline_node = coordinator.registry[timeline_node_id]
    if timeline_node.resource_history:
        tl_df = pd.DataFrame(timeline_node.resource_history)
        tl_chart = (
            alt.Chart(tl_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("timestamp:Q", title="Simulation Time (s)"),
                y=alt.Y("sync_interval_ms:Q", title="Sync Interval (ms)"),
                tooltip=["step", "timestamp", "sync_interval_ms", "beacon_interval_ms", "transmit_power_pct"],
            )
        )
        st.altair_chart(tl_chart, use_container_width=True)
        st.caption(
            "Synchronization-interval evolution over time for the selected node, "
            "showing ARAC re-allocating resources as the node's state changes "
            "(Sprint 9 Deliverable 18)."
        )
    else:
        st.markdown(
            '<div class="psdt-placeholder-box">No resource history yet for this node.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("###### Estimated Energy & Communication Statistics")
    counts = coordinator.get_packet_counts()
    total_radio_active = sum(n.radio_active_time for n in coordinator.registry.values())
    total_energy = sum(n.energy_consumed for n in coordinator.registry.values())
    fixed_energy_estimate = total_radio_active * ENERGY_COST_PER_ACTIVE_SECOND_BY_LEVEL[FIXED_BASELINE_TRANSMIT_POWER_LEVEL]
    saving_pct = (
        (fixed_energy_estimate - total_energy) / fixed_energy_estimate * 100.0
        if fixed_energy_estimate
        else 0.0
    )
    sim_time = st.session_state.get("dt_sim_time", 0.0)
    beacon_count_est = sum(
        sim_time / (n.allocated_beacon_interval_ms / 1000.0)
        for n in adaptive_nodes
        if n.allocated_beacon_interval_ms
    )

    energy_cols = st.columns(4)
    energy_cols[0].metric("Radio Active Time", f"{total_radio_active:.2f} s")
    energy_cols[1].metric("Estimated Battery Consumption", f"{total_energy:.3f} J")
    energy_cols[2].metric("Estimated Energy Saving", f"{saving_pct:.1f} %")
    energy_cols[3].metric("Synchronization Packets", counts["received"])

    comm_cols = st.columns(3)
    comm_cols[0].metric("Beacon Count (est.)", f"{beacon_count_est:.0f}")
    comm_cols[1].metric("Control Packets (PRAP)", coordinator.prap_generated)
    comm_cols[2].metric("Resource Updates", coordinator.prap_generated)
    st.caption(
        "Radio active time, battery consumption, and energy saving are estimated "
        "values derived from the simulation model (allocated wake-up interval and "
        "transmit power), not direct hardware measurements (Sprint 9 Deliverable "
        "15). In this simulator, PRAP packets serve as both the control-packet and "
        "resource-update mechanism (Sprint 9 Deliverable 16)."
    )
else:
    st.markdown(
        '<div class="psdt-placeholder-box">Run a communication cycle on the '
        'Simulation page to populate Resource Allocation analytics.</div>',
        unsafe_allow_html=True,
    )
