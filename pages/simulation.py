import streamlit as st
import pandas as pd

from core.constants import NODE_COUNT_OPTIONS, ZONE_ORDER
from core.node_factory import generate_nodes
from core.coordinator import CentralSynchronizationCoordinator, PIPELINE_STAGES
from core.threshold_profiles import CALIBRATION_FACTORS, MOTION_FACTORS, ENVIRONMENT_FACTORS, CUSTOM_CALIBRATION_BOUNDS
from core.error_profiles import (
    DEFAULT_WEIGHTS,
    WEIGHT_BOUNDS,
    NETWORK_CONDITION_ADJUSTMENT_MS,
    DEFAULT_NETWORK_CONDITION,
)
from core.simulation_engine import DigitalTwinSimulationEngine
from core.sce import STATE_ORDER, RELAXED, NOMINAL, ELEVATED, IMMEDIATE
from config.simulation_profiles import (
    DURATION_OPTIONS_S,
    TIME_STEP_OPTIONS_S,
    DEFAULT_DURATION_S,
    DEFAULT_TIME_STEP_S,
    DEFAULT_SEED,
    NETWORK_PROFILE_OPTIONS,
    DEFAULT_NETWORK_PROFILE,
    SCENARIO_OPTIONS,
    DEFAULT_SCENARIO,
)

st.title("Simulation") 
st.markdown("---")
st.header("Live Digital Twin (Sprint 10)")
st.markdown("### Digital Twin Control")
st.caption(
    "A time-evolving closed-loop simulation: Node State(t) -> DTCE -> PEEE -> "
    "PSME -> SCE -> ARAC -> Resource Action -> Node State(t+dt). Simulated time "
    "is decoupled from wall-clock time, so a full run completes in well under a "
    "second regardless of the configured duration (Sprint 10 Deliverable 2)."
)

ctrl_cols = st.columns(6)
with ctrl_cols[0]:
    s10_nodes = st.selectbox("Nodes", NODE_COUNT_OPTIONS, index=NODE_COUNT_OPTIONS.index(30), key="s10_nodes")
with ctrl_cols[1]:
    s10_duration = st.selectbox("Duration (s)", DURATION_OPTIONS_S, index=DURATION_OPTIONS_S.index(DEFAULT_DURATION_S), key="s10_duration")
with ctrl_cols[2]:
    s10_dt = st.selectbox("Time Step (s)", TIME_STEP_OPTIONS_S, index=TIME_STEP_OPTIONS_S.index(DEFAULT_TIME_STEP_S), key="s10_dt")
with ctrl_cols[3]:
    s10_seed = st.number_input("Seed", value=DEFAULT_SEED, step=1, key="s10_seed")
with ctrl_cols[4]:
    s10_network = st.selectbox("Network Profile", NETWORK_PROFILE_OPTIONS, index=NETWORK_PROFILE_OPTIONS.index(DEFAULT_NETWORK_PROFILE), key="s10_network")
with ctrl_cols[5]:
    s10_scenario = st.selectbox("Context Scenario", SCENARIO_OPTIONS, index=SCENARIO_OPTIONS.index(DEFAULT_SCENARIO), key="s10_scenario")

s10_history_mode = st.radio(
    "History Mode", ["Interactive (bounded)", "Experiment (complete)"],
    horizontal=True, key="s10_history_mode",
)

btn_cols = st.columns(5)
init_clicked = btn_cols[0].button("Initialize", use_container_width=True, key="s10_init_btn")
run_clicked = btn_cols[1].button("Run", use_container_width=True, key="s10_run_btn")
pause_clicked = btn_cols[2].button("Pause", use_container_width=True, key="s10_pause_btn")
step_clicked = btn_cols[3].button("Step", use_container_width=True, key="s10_step_btn")
reset_clicked = btn_cols[4].button("Reset", use_container_width=True, key="s10_reset_btn")

if init_clicked or reset_clicked:
    new_engine = DigitalTwinSimulationEngine(
        num_nodes=s10_nodes, duration_s=s10_duration, time_step_s=s10_dt, seed=int(s10_seed),
        network_profile=s10_network, scenario=s10_scenario,
        history_mode="experiment" if s10_history_mode.startswith("Experiment") else "interactive",
    )
    new_engine.initialize()
    st.session_state.s10_engine = new_engine

s10_engine = st.session_state.get("s10_engine")

if run_clicked and s10_engine is not None:
    s10_engine.run_to_completion()

if step_clicked and s10_engine is not None:
    s10_engine.step()

if pause_clicked and s10_engine is not None:
    st.info("Run completes synchronously in one click since simulated time is decoupled from wall-clock time (Deliverable 2); use Step to advance one cycle at a time instead.")

if s10_engine is None:
    st.info("Click Initialize to create a Digital Twin simulation run.")
else:
    s10_status = s10_engine.status()

    st.markdown("**Simulation Status**")
    status_cols = st.columns(4)
    status_cols[0].metric("Simulation Time", f"{s10_status['sim_time']:.0f} / {s10_status['duration_s']:.0f} s")
    status_cols[1].metric("Active Nodes", s10_status["active_nodes"])
    status_cols[2].metric("Current Cycle", s10_status["cycle"])
    status_cols[3].metric("Sync Events", s10_status["sync_events"])

    status_cols2 = st.columns(4)
    status_cols2[0].metric("State Transitions", s10_status["state_transitions"])
    status_cols2[1].metric("PRAPs Applied", s10_status["prap_applied"])
    status_cols2[2].metric("Energy Consumed", f"{s10_status['energy_consumed_j']:.3f} J")
    status_cols2[3].metric("Invariant Violations", s10_status["invariant_violations"])

    if s10_status["finished"]:
        st.success("Run complete.")
    if s10_status["invariant_violations"]:
        st.warning(f"{s10_status['invariant_violations']} invariant violation(s) were logged - see Event Log.")

    s10_node_ids = list(s10_engine.coordinator.registry.keys())
    st.markdown("---")
    st.markdown("### Live Node Inspector")
    s10_selected_node_id = st.selectbox("Select a node", s10_node_ids, key="s10_selected_node")

    if s10_selected_node_id:
        s10_inspector = s10_engine.node_inspector(s10_selected_node_id)
        s10_node = s10_inspector["node"]

        insp_cols = st.columns(4)
        insp_cols[0].metric("PT", f"{s10_node.perceptual_threshold:.2f} ms" if s10_node.perceptual_threshold is not None else "-")
        insp_cols[1].metric("PE", f"{s10_node.perceived_error:.2f} ms" if s10_node.perceived_error is not None else "-")
        insp_cols[2].metric("PSM", f"{s10_node.psm:.2f} ms" if s10_node.psm is not None else "-")
        insp_cols[3].metric("NPSM", f"{s10_node.normalized_psm:.3f}" if s10_node.normalized_psm is not None else "-")

        insp_cols2 = st.columns(4)
        insp_cols2[0].metric("State", s10_node.sync_state)
        insp_cols2[1].metric("Previous State", s10_node.previous_state or "-")
        insp_cols2[2].metric("Sync Interval", f"{s10_engine.allocated_sync_interval_ms(s10_node):.0f} ms")
        insp_cols2[3].metric("TX Power", s10_node.allocated_transmit_power_level or "-")

        insp_cols3 = st.columns(4)
        insp_cols3[0].metric("Energy Used", f"{s10_node.energy_consumed:.3f} J")
        insp_cols3[1].metric("Battery", f"{s10_node.battery_level:.2f} %")
        insp_cols3[2].metric("Last Sync", f"{s10_inspector['last_sync_time_s']:.1f} s" if s10_inspector["last_sync_time_s"] is not None else "-")
        insp_cols3[3].metric("Next Sync (est.)", f"{s10_inspector['next_sync_due_s']:.1f} s" if s10_inspector["next_sync_due_s"] is not None else "-")

        s10_series = s10_inspector["series"]
        if s10_series["timestamp"]:
            s10_df_pt = pd.DataFrame({
                "time_s": s10_series["timestamp"],
                "PT (ms)": s10_series["PT"],
                "PE (ms)": s10_series["PE"],
                "PSM (ms)": s10_series["PSM"],
            }).set_index("time_s")
            st.markdown("**PT / PE / PSM over time**")
            st.line_chart(s10_df_pt)

            s10_state_code = {IMMEDIATE: 0, ELEVATED: 1, NOMINAL: 2, RELAXED: 3}
            s10_df_state = pd.DataFrame({
                "time_s": s10_series["timestamp"],
                "state_code": [s10_state_code.get(s) for s in s10_series["current_state"]],
            }).set_index("time_s")
            st.markdown("**State Timeline** (0=IMMEDIATE, 1=ELEVATED, 2=NOMINAL, 3=RELAXED)")
            st.line_chart(s10_df_state)

            s10_df_resource = pd.DataFrame({
                "time_s": s10_series["timestamp"],
                "Sync Interval (ms)": s10_series["sync_interval_ms"],
                "Beacon Interval (ms)": s10_series["beacon_interval_ms"],
                "TX Power (%)": s10_series["tx_power_pct"],
            }).set_index("time_s")
            st.markdown("**Resource-Control Timeline**")
            st.line_chart(s10_df_resource)

        with st.expander("Recent events for this node"):
            for s10_event in s10_inspector["recent_events"]:
                st.text(f"T={s10_event['timestamp']:.1f}s  {s10_event['message']}")

    st.markdown("---")
    st.markdown("### Global Digital Twin Dashboard")
    dash_cols = st.columns(2)
    with dash_cols[0]:
        st.markdown("**Current State Distribution**")
        st.bar_chart(pd.DataFrame.from_dict(s10_status["state_counts"], orient="index", columns=["Nodes"]))
    with dash_cols[1]:
        s10_global_series = s10_engine.history.global_dataframe_dict()
        if s10_global_series["timestamp"]:
            s10_df_global = pd.DataFrame({
                "time_s": s10_global_series["timestamp"],
                "Mean PT": s10_global_series["mean_pt"],
                "Mean PE": s10_global_series["mean_pe"],
                "Mean PSM": s10_global_series["mean_psm"],
            }).set_index("time_s")
            st.markdown("**Mean PT / PE / PSM over time**")
            st.line_chart(s10_df_global)

    dash_metric_cols = st.columns(4)
    dash_metric_cols[0].metric("Total Sync Events", s10_status["sync_events"])
    s10_total_messages = s10_engine.coordinator.get_packet_counts()["generated"] + s10_engine.coordinator.prap_generated + s10_status["sync_events"]
    dash_metric_cols[1].metric("Total Communication Messages", s10_total_messages)
    dash_metric_cols[2].metric("Total Estimated Energy", f"{s10_status['energy_consumed_j']:.3f} J")
    s10_mean_battery = sum(n.battery_level for n in s10_engine.coordinator.registry.values()) / len(s10_node_ids)
    dash_metric_cols[3].metric("Mean Battery Remaining", f"{s10_mean_battery:.2f} %")

    st.markdown("---")
    st.markdown("### Body-Zone Analytics")
    s10_zone_summary = s10_engine.body_zone_summary()
    s10_zone_rows = []
    for s10_zone in ZONE_ORDER:
        s10_z = s10_zone_summary.get(s10_zone)
        if not s10_z:
            continue
        s10_zone_rows.append({
            "Zone": s10_zone, "Nodes": s10_z["count"],
            "Mean PT (ms)": round(s10_z["mean_pt"], 2) if s10_z["mean_pt"] is not None else None,
            "Mean PE (ms)": round(s10_z["mean_pe"], 2) if s10_z["mean_pe"] is not None else None,
            "Mean PSM (ms)": round(s10_z["mean_psm"], 2) if s10_z["mean_psm"] is not None else None,
            "Mean Sync Interval (ms)": round(s10_z["mean_sync_interval_ms"], 1),
            "Sync Events (last step)": s10_z["sync_events_this_step"],
            "Estimated Energy (J)": round(s10_z["energy_j"], 3),
        })
    st.dataframe(pd.DataFrame(s10_zone_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Event Log")
    with st.expander("Recent simulation events", expanded=False):
        for s10_event in s10_engine.history.recent_events(150):
            st.text(f"T={s10_event['timestamp']:.1f}s  {s10_event['node_id']}  {s10_event['message']}")

    st.markdown("---")
    st.markdown("### Disturbance Injection")
    st.caption("Applies immediately to the current simulation state; effects propagate through the next Step/Run (Deliverable 28).")
    s10_dist_target = st.selectbox("Target", ["ALL"] + s10_node_ids, key="s10_dist_target")
    s10_target_id = None if s10_dist_target == "ALL" else s10_dist_target
    dist_cols = st.columns(4)
    if dist_cols[0].button("Inject Network Jitter", key="s10_dist_jitter"):
        s10_engine.inject_network_jitter(s10_target_id)
    if dist_cols[1].button("Inject Clock Drift Spike", key="s10_dist_drift"):
        s10_engine.inject_clock_drift_spike(s10_target_id)
    if dist_cols[2].button("Increase Environmental Disturbance", key="s10_dist_env"):
        s10_engine.increase_environmental_disturbance()
    s10_dist_motion = dist_cols[3].selectbox("Change Motion State", ["(scenario default)", "Stationary", "Walking", "Running"], key="s10_dist_motion")
    if s10_dist_motion != "(scenario default)":
        s10_engine.set_motion_state(s10_dist_motion)
    else:
        s10_engine.clear_manual_overrides()

st.markdown("---")
st.header("Manual Engine Testing (Sprint 3-9)")


# ---------------------------------------------------------------------
# Digital Twin Configuration
# ---------------------------------------------------------------------
st.subheader("Digital Twin Configuration")

st.markdown('<div class="psdt-card">', unsafe_allow_html=True)
cfg_cols = st.columns(4)
with cfg_cols[0]:
    num_nodes = st.selectbox(
        "Number of Nodes", NODE_COUNT_OPTIONS, index=NODE_COUNT_OPTIONS.index(30)
    )
with cfg_cols[1]:
    seed = st.number_input("Random Seed", min_value=0, max_value=999999, value=42, step=1)
with cfg_cols[2]:
    duration = st.number_input(
        "Simulation Duration (seconds)", min_value=1, value=3600, step=1
    )
with cfg_cols[3]:
    time_step = st.number_input("Time Step (seconds)", min_value=1, value=1, step=1)

initialize = st.button("Initialize Digital Twin", type="primary", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if initialize:
    nodes = generate_nodes(int(num_nodes), seed=int(seed))
    coordinator = CentralSynchronizationCoordinator(seed=int(seed))
    coordinator.register_nodes(nodes)

    st.session_state.dt_nodes = nodes
    st.session_state.dt_coordinator = coordinator
    st.session_state.dt_sim_time = 0.0
    st.session_state.dt_config = {
        "num_nodes": int(num_nodes),
        "seed": int(seed),
        "duration": int(duration),
        "time_step": int(time_step),
    }

nodes = st.session_state.get("dt_nodes")
config = st.session_state.get("dt_config")
coordinator = st.session_state.get("dt_coordinator")

if not nodes:
    st.markdown(
        '<div class="psdt-placeholder-box-lg">Configure the parameters above and click '
        '&quot;Initialize Digital Twin&quot; to generate the wearable node network.</div>',
        unsafe_allow_html=True,
    )
else:
    st.caption(
        f"Active network: {config['num_nodes']} nodes | seed {config['seed']} | "
        f"duration {config['duration']}s | step {config['time_step']}s"
    )

    # -------------------------------------------------------------
    # Virtual wearable topology
    # -------------------------------------------------------------
    st.subheader("Virtual Wearable Topology")

    zone_display = {
        "Fingertip": "FINGERTIPS",
        "Hand": "HANDS",
        "Forearm": "FOREARMS",
        "Torso": "TORSO",
        "Leg": "LEGS",
        "Foot": "FEET",
    }

    topology_html = '<div class="psdt-card">'
    for zone in ZONE_ORDER:
        count = len([n for n in nodes if n.body_zone == zone])
        dots = " ".join(["●"] * count) if count else "—"
        topology_html += (
            f'<div class="psdt-zone-label">{zone_display[zone]}</div>'
            f'<div class="psdt-zone-dots">{dots}</div>'
        )
    topology_html += "</div>"
    st.markdown(topology_html, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Node Inspector + Node Table
    # -------------------------------------------------------------
    inspector_col, table_col = st.columns([1, 2])
    node_ids = [n.node_id for n in nodes]

    with inspector_col:
        st.subheader("Node Inspector")
        selected_id = st.selectbox("Select Node", node_ids)
        selected_node = next(n for n in nodes if n.node_id == selected_id)

        def fmt(value, suffix=""):
            return "Not computed" if value is None else f"{value}{suffix}"

        sync_state_display = (
            "Awaiting Sprint 8 classification"
            if selected_node.sync_state == "Unclassified"
            else selected_node.sync_state
        )

        previous_state_display = (
            "None yet"
            if selected_node.previous_state is None
            else selected_node.previous_state
        )

        st.markdown(
            f"""
            <div class="psdt-card">
            <p style="margin:0 0 0.4rem 0;"><b>Node ID</b><br>{selected_node.node_id}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Body Zone</b><br>{selected_node.body_zone}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Actuator</b><br>{selected_node.actuator_type}</p>
            <p style="margin:0 0 0.8rem 0;"><b>Frequency</b><br>{selected_node.vibration_frequency} Hz</p>
            <hr style="margin:0.6rem 0;">
            <p style="margin:0 0 0.4rem 0;"><b>Battery</b><br>{selected_node.battery_level} %</p>
            <p style="margin:0 0 0.4rem 0;"><b>Clock Drift</b><br>{selected_node.clock_drift} ms</p>
            <p style="margin:0 0 0.4rem 0;"><b>Network Delay</b><br>{selected_node.network_delay} ms</p>
            <p style="margin:0 0 0.4rem 0;"><b>Actuator Driver Delay</b><br>{selected_node.actuator_driver_delay} ms</p>
            <p style="margin:0 0 0.8rem 0;"><b>Mechanical Delay</b><br>{selected_node.mechanical_startup_delay} ms</p>
            <hr style="margin:0.6rem 0;">
            <p style="margin:0 0 0.4rem 0;"><b>PT (Dynamic)</b><br>{fmt(round(selected_node.perceptual_threshold, 2) if selected_node.perceptual_threshold is not None else None, " ms")}</p>
            <p style="margin:0 0 0.4rem 0;"><b>PE</b><br>{fmt(round(selected_node.perceived_error, 2) if selected_node.perceived_error is not None else None, " ms")}</p>
            <p style="margin:0 0 0.4rem 0;"><b>PSM</b><br>{fmt(round(selected_node.psm, 2) if selected_node.psm is not None else None, " ms")}</p>
            <p style="margin:0 0 0.4rem 0;"><b>NPSM</b><br>{fmt(round(selected_node.normalized_psm, 4) if selected_node.normalized_psm is not None else None)}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Threshold Utilization</b><br>{fmt(round(selected_node.threshold_utilization_pct, 2) if selected_node.threshold_utilization_pct is not None else None, "%")}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Margin Sign</b><br>{fmt(selected_node.margin_sign)}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Current State</b><br>{sync_state_display}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Previous State</b><br>{previous_state_display}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Transition</b><br>{"Yes" if selected_node.transition_flag else "No"}</p>
            <p style="margin:0;"><b>Persistence Counter</b><br>{selected_node.persistence_counter}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("State History (last cycles)"):
            if selected_node.state_history:
                hist_df = pd.DataFrame(selected_node.state_history[-10:])
                st.dataframe(hist_df, hide_index=True, use_container_width=True)
            else:
                st.markdown(
                    '<div class="psdt-placeholder-box">No state history yet - run a communication cycle.</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("##### Resource Allocation (ARAC)")
        st.markdown(
            f"""
            <div class="psdt-card">
            <p style="margin:0 0 0.4rem 0;"><b>Status</b><br>{selected_node.resource_status}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Sync Interval</b><br>{fmt(selected_node.allocated_sync_interval_ms, " ms")}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Beacon Interval</b><br>{fmt(selected_node.allocated_beacon_interval_ms, " ms")}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Radio Wake-up Interval</b><br>{fmt(selected_node.allocated_radio_wakeup_interval_ms, " ms")}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Transmit Power</b><br>{fmt(selected_node.allocated_transmit_power_level)} ({fmt(selected_node.allocated_transmit_power_pct, "%")})</p>
            <p style="margin:0;"><b>Trigger Offset</b><br>{fmt(selected_node.allocated_trigger_offset_ms, " ms")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Resource History (last cycles)"):
            if selected_node.resource_history:
                res_hist_df = pd.DataFrame(selected_node.resource_history[-10:])
                st.dataframe(res_hist_df, hide_index=True, use_container_width=True)
            else:
                st.markdown(
                    '<div class="psdt-placeholder-box">No resource history yet - run a communication cycle.</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("##### Dynamic Threshold Characterization")
        audit = coordinator.dtce_audit.get(selected_id) if coordinator else None
        if audit:
            st.markdown(
                f"""
                <div class="psdt-card">
                <p style="margin:0 0 0.3rem 0;">Body Zone: <b>{audit.body_zone}</b></p>
                <p style="margin:0 0 0.3rem 0;">Baseline PT: <b>{audit.base_pt_ms:.2f} ms</b></p>
                <p style="margin:0 0 0.3rem 0;">Frequency: <b>{audit.frequency_hz:.0f} Hz</b>
                &nbsp;&nbsp; Frequency Factor: <b>x{audit.frequency_factor:.2f}</b></p>
                <p style="margin:0 0 0.3rem 0;">Actuator: <b>{audit.actuator_type}</b>
                &nbsp;&nbsp; Actuator Factor: <b>x{audit.actuator_factor:.2f}</b></p>
                <p style="margin:0 0 0.3rem 0;">Calibration: <b>{audit.calibration_profile}</b>
                &nbsp;&nbsp; Calibration Factor: <b>x{audit.calibration_factor:.2f}</b></p>
                <p style="margin:0 0 0.3rem 0;">Motion: <b>{audit.motion_state}</b>
                &nbsp;&nbsp; Motion Factor: <b>x{audit.motion_factor:.2f}</b></p>
                <p style="margin:0 0 0.6rem 0;">Environment: <b>{audit.environment_state}</b>
                &nbsp;&nbsp; Environment Factor: <b>x{audit.environment_factor:.2f}</b></p>
                <hr style="margin:0.6rem 0;">
                <p style="margin:0; font-weight:600;">Dynamic Perceptual Threshold PTz(t):
                {audit.dynamic_pt_ms:.2f} ms</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="psdt-placeholder-box">Run a communication cycle to compute '
                'this node&#39;s Dynamic Perceptual Threshold.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("##### Perceived Error Estimation")
        peee_audit = coordinator.peee_audit.get(selected_id) if coordinator else None
        if peee_audit:
            st.markdown(
                f"""
                <div class="psdt-card">
                <p style="margin:0 0 0.3rem 0;">Clock Drift (CD): <b>{peee_audit.cd_ms:.2f} ms</b></p>
                <p style="margin:0 0 0.3rem 0;">Network Residual (ND): <b>{peee_audit.nd_ms:.2f} ms</b></p>
                <p style="margin:0 0 0.3rem 0;">Actuator Driver (AD): <b>{peee_audit.ad_ms:.2f} ms</b></p>
                <p style="margin:0 0 0.6rem 0;">Mechanical Startup (MD): <b>{peee_audit.md_ms:.2f} ms</b></p>
                <hr style="margin:0.6rem 0;">
                <p style="margin:0 0 0.3rem 0;">Model Used: <b>{peee_audit.model.title()} Residual</b></p>
                <p style="margin:0 0 0.3rem 0;">Weights: CD x{peee_audit.weight_cd:.2f} &nbsp; ND x{peee_audit.weight_nd:.2f}
                &nbsp; AD x{peee_audit.weight_ad:.2f} &nbsp; MD x{peee_audit.weight_md:.2f}</p>
                <p style="margin:0 0 0.6rem 0;">Contributions: CD {peee_audit.contribution_cd:.2f} + ND {peee_audit.contribution_nd:.2f}
                + AD {peee_audit.contribution_ad:.2f} + MD {peee_audit.contribution_md:.2f}</p>
                <hr style="margin:0.6rem 0;">
                <p style="margin:0; font-weight:600;">Estimated Perceived Error PEz(t):
                {peee_audit.perceived_error_ms:.2f} ms</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="psdt-placeholder-box">Run a communication cycle to compute '
                'this node&#39;s Estimated Perceived Error.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("##### Perceptual Synchronization Margin")
        psme_result = coordinator.psme_audit.get(selected_id) if coordinator else None
        if psme_result and psme_result.status == "INVALID_INPUT":
            st.markdown(
                f'<div class="psdt-placeholder-box">PSME rejected this node\'s inputs: '
                f'{psme_result.error_reason}</div>',
                unsafe_allow_html=True,
            )
        elif psme_result:
            st.markdown(
                f"""
                <div class="psdt-card">
                <p style="margin:0 0 0.3rem 0;">PT: <b>{psme_result.pt_ms:.2f} ms</b></p>
                <p style="margin:0 0 0.3rem 0;">PE: <b>{psme_result.pe_ms:.2f} ms</b></p>
                <p style="margin:0 0 0.6rem 0;">PSM = PT - PE = {psme_result.pt_ms:.2f} - {psme_result.pe_ms:.2f} = <b>{psme_result.psm_ms:+.2f} ms</b></p>
                <p style="margin:0 0 0.3rem 0;">Normalized PSM: <b>{psme_result.normalized_psm:.4f}</b></p>
                <p style="margin:0 0 0.3rem 0;">Threshold Utilization: <b>{psme_result.threshold_utilization_pct:.2f}%</b></p>
                <p style="margin:0;">Margin Sign: <b>{psme_result.margin_sign}</b></p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("###### PSM Gauge")
            gauge_scale = max(psme_result.pt_ms, psme_result.pe_ms) * 1.15
            pe_pct = min(100.0, (psme_result.pe_ms / gauge_scale) * 100.0)
            pt_pct = min(100.0, (psme_result.pt_ms / gauge_scale) * 100.0)

            if psme_result.psm_ms >= 0:
                used_pct = pe_pct
                margin_pct = max(0.0, pt_pct - pe_pct)
                gauge_bar = (
                    f'<div style="position:relative; height:26px; background:#1E293B; '
                    f'border-radius:6px; overflow:hidden;">'
                    f'<div style="position:absolute; left:0; top:0; height:100%; width:{used_pct:.2f}%; '
                    f'background:#3B82F6;"></div>'
                    f'<div style="position:absolute; left:{used_pct:.2f}%; top:0; height:100%; '
                    f'width:{margin_pct:.2f}%; background:#16A34A;"></div>'
                    f'<div style="position:absolute; left:{pt_pct:.2f}%; top:0; height:100%; '
                    f'width:2px; background:#F8FAFC;"></div>'
                    f'</div>'
                )
                legend = (
                    f'<div style="display:flex; justify-content:space-between; font-size:0.72rem; '
                    f'color:#94A3B8; margin-top:0.3rem;">'
                    f'<span>0 ms</span>'
                    f'<span style="color:#3B82F6;">used (PE): {psme_result.pe_ms:.2f} ms</span>'
                    f'<span style="color:#16A34A;">margin (PSM): +{psme_result.psm_ms:.2f} ms</span>'
                    f'<span>PT: {psme_result.pt_ms:.2f} ms</span>'
                    f'</div>'
                )
            else:
                exceeded_pct = max(0.0, pe_pct - pt_pct)
                gauge_bar = (
                    f'<div style="position:relative; height:26px; background:#1E293B; '
                    f'border-radius:6px; overflow:hidden;">'
                    f'<div style="position:absolute; left:0; top:0; height:100%; width:{pt_pct:.2f}%; '
                    f'background:#3B82F6;"></div>'
                    f'<div style="position:absolute; left:{pt_pct:.2f}%; top:0; height:100%; '
                    f'width:{exceeded_pct:.2f}%; background:#DC2626;"></div>'
                    f'<div style="position:absolute; left:{pt_pct:.2f}%; top:0; height:100%; '
                    f'width:2px; background:#F8FAFC;"></div>'
                    f'</div>'
                )
                legend = (
                    f'<div style="display:flex; justify-content:space-between; font-size:0.72rem; '
                    f'color:#94A3B8; margin-top:0.3rem;">'
                    f'<span>0 ms</span>'
                    f'<span>PT: {psme_result.pt_ms:.2f} ms</span>'
                    f'<span style="color:#DC2626;">exceeded by {abs(psme_result.psm_ms):.2f} ms '
                    f'(PE: {psme_result.pe_ms:.2f} ms)</span>'
                    f'</div>'
                )

            st.markdown(f'<div class="psdt-card">{gauge_bar}{legend}</div>', unsafe_allow_html=True)
            st.caption(
                "Blue marks perceived error consumed against the threshold. Green marks the "
                "remaining margin (PSM). Red marks the amount by which PE exceeds PT when the "
                "margin is negative. The white tick marks PTz(t); this is a visual aid only and "
                "assigns no synchronization state."
            )
        else:
            st.markdown(
                '<div class="psdt-placeholder-box">Run a communication cycle to compute '
                'this node&#39;s Perceptual Synchronization Margin.</div>',
                unsafe_allow_html=True,
            )

    with table_col:
        st.subheader("Node Table")
        zone_filter = st.multiselect("Filter by body zone", ZONE_ORDER, default=ZONE_ORDER)

        rows = [
            {
                "Node ID": n.node_id,
                "Zone": n.body_zone,
                "Actuator": n.actuator_type,
                "CD (ms)": n.clock_drift,
                "ND (ms)": n.network_delay,
                "AD (ms)": n.actuator_driver_delay,
                "MD (ms)": n.mechanical_startup_delay,
                "PT (ms)": round(n.perceptual_threshold, 2) if n.perceptual_threshold is not None else None,
                "PE (ms)": round(n.perceived_error, 2) if n.perceived_error is not None else None,
                "PSM (ms)": round(n.psm, 2) if n.psm is not None else None,
                "NPSM": round(n.normalized_psm, 4) if n.normalized_psm is not None else None,
                "Threshold Utilization (%)": round(n.threshold_utilization_pct, 2) if n.threshold_utilization_pct is not None else None,
                "Margin Sign": n.margin_sign,
                "Battery (%)": n.battery_level,
                "State": n.sync_state,
                "Previous State": n.previous_state,
                "Transition": n.transition_flag,
                "Persistence": n.persistence_counter,
                "Resource Status": n.resource_status,
                "Sync Interval (ms)": n.allocated_sync_interval_ms,
                "Beacon (ms)": n.allocated_beacon_interval_ms,
                "Wake-up (ms)": n.allocated_radio_wakeup_interval_ms,
                "TX Power": n.allocated_transmit_power_level,
                "Trigger Offset (ms)": n.allocated_trigger_offset_ms,
            }
            for n in nodes
            if n.body_zone in zone_filter
        ]

        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

        # -----------------------------------------------------------------
        # DTCE audit table
        # -----------------------------------------------------------------
        st.subheader("DTCE Audit Table")
        if coordinator and coordinator.dtce_audit:
            audit_rows = [
                {
                    "Node": nid,
                    "Zone": a.body_zone,
                    "Base PT (ms)": round(a.base_pt_ms, 2),
                    "Freq Factor": a.frequency_factor,
                    "Actuator Factor": a.actuator_factor,
                    "UCF": a.calibration_factor,
                    "Motion": a.motion_state,
                    "Motion Factor": a.motion_factor,
                    "Environment": a.environment_state,
                    "Env Factor": a.environment_factor,
                    "Dynamic PT (ms)": round(a.dynamic_pt_ms, 2),
                }
                for nid, a in coordinator.dtce_audit.items()
            ]
            st.dataframe(pd.DataFrame(audit_rows), hide_index=True, use_container_width=True)
        else:
            st.markdown(
                '<div class="psdt-placeholder-box">Run a communication cycle to populate the DTCE audit table.</div>',
                unsafe_allow_html=True,
            )

        # -----------------------------------------------------------------
        # PEEE audit table
        # -----------------------------------------------------------------
        st.subheader("PEEE Audit Table")
        if coordinator and coordinator.peee_audit:
            peee_rows = [
                {
                    "Node": nid,
                    "Zone": a.body_zone,
                    "CD (ms)": round(a.cd_ms, 2),
                    "ND (ms)": round(a.nd_ms, 2),
                    "AD (ms)": round(a.ad_ms, 2),
                    "MD (ms)": round(a.md_ms, 2),
                    "Model": a.model,
                    "W-CD": a.weight_cd,
                    "W-ND": a.weight_nd,
                    "W-AD": a.weight_ad,
                    "W-MD": a.weight_md,
                    "PE (ms)": round(a.perceived_error_ms, 2),
                }
                for nid, a in coordinator.peee_audit.items()
            ]
            st.dataframe(pd.DataFrame(peee_rows), hide_index=True, use_container_width=True)
        else:
            st.markdown(
                '<div class="psdt-placeholder-box">Run a communication cycle to populate the PEEE audit table.</div>',
                unsafe_allow_html=True,
            )

        # -------------------------------------------------------------
        # ARAC audit table
        # -------------------------------------------------------------
        st.subheader("ARAC Audit Table")
        if coordinator and coordinator.arac_audit:
            arac_rows = [
                {
                    "Node": nid,
                    "Zone": coordinator.registry[nid].body_zone,
                    "State": r.target_state,
                    "Sync Interval (ms)": r.sync_interval_ms,
                    "Beacon (ms)": r.beacon_interval_ms,
                    "Wake-up (ms)": r.radio_wakeup_interval_ms,
                    "TX Power": r.transmit_power_level,
                    "Trigger Offset (ms)": r.trigger_timing_offset_ms,
                    "Status": r.status,
                }
                for nid, r in coordinator.arac_audit.items()
            ]
            st.dataframe(pd.DataFrame(arac_rows), hide_index=True, use_container_width=True)
        else:
            st.markdown(
                '<div class="psdt-placeholder-box">Run a communication cycle to populate the ARAC audit table.</div>',
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------
    # Central Synchronization Coordinator
    # -------------------------------------------------------------
    st.subheader("Central Synchronization Coordinator")

    counts = coordinator.get_packet_counts()
    metric_cols = st.columns(4)
    metric_cols[0].metric("Registered Nodes", coordinator.registered_node_count)
    metric_cols[1].metric("PSSPs Received", counts["received"])
    metric_cols[2].metric("Valid Packets", counts["valid"])
    metric_cols[3].metric("PRAPs Generated", coordinator.prap_generated)

    st.markdown("###### Perceptual Context")
    ctx_cols = st.columns(4)
    with ctx_cols[0]:
        calibration_profile = st.selectbox(
            "User Profile", list(CALIBRATION_FACTORS.keys()) + ["Custom"], key="dtce_calibration_profile"
        )
    with ctx_cols[1]:
        custom_calibration_factor = None
        if calibration_profile == "Custom":
            lo, hi = CUSTOM_CALIBRATION_BOUNDS
            custom_calibration_factor = st.slider(
                "Custom UCF", min_value=lo, max_value=hi, value=1.0, step=0.01, key="dtce_custom_ucf"
            )
        else:
            st.caption(f"UCF = x{CALIBRATION_FACTORS[calibration_profile]:.2f}")
    with ctx_cols[2]:
        motion_state = st.selectbox("Motion State", list(MOTION_FACTORS.keys()), key="dtce_motion_state")
    with ctx_cols[3]:
        environment_state = st.selectbox(
            "Environment", list(ENVIRONMENT_FACTORS.keys()), key="dtce_environment_state"
        )

    recalculate = st.button("Recalculate Thresholds", use_container_width=True)
    if recalculate:
        coordinator.set_perceptual_context(
            calibration_profile=calibration_profile,
            custom_calibration_factor=custom_calibration_factor,
            motion_state=motion_state,
            environment_state=environment_state,
        )
        coordinator.run_dtce_pass()
        st.rerun()

    st.markdown("###### Perceived Error Model")
    pe_cols = st.columns(2)
    with pe_cols[0]:
        pe_model_label = st.radio(
            "Perceived Error Model",
            ["Additive Residual", "Weighted Residual"],
            key="peee_model_choice",
        )
        pe_model = "additive" if pe_model_label == "Additive Residual" else "weighted"
    with pe_cols[1]:
        network_condition = st.selectbox(
            "Network Condition",
            list(NETWORK_CONDITION_ADJUSTMENT_MS.keys()),
            index=list(NETWORK_CONDITION_ADJUSTMENT_MS.keys()).index(DEFAULT_NETWORK_CONDITION),
            key="peee_network_condition",
        )

    pe_weights = dict(DEFAULT_WEIGHTS)
    if pe_model == "weighted":
        with st.expander("Advanced Experimental Settings", expanded=True):
            w_cols = st.columns(4)
            with w_cols[0]:
                pe_weights["CD"] = st.number_input(
                    "CD Weight", min_value=WEIGHT_BOUNDS[0], max_value=WEIGHT_BOUNDS[1],
                    value=DEFAULT_WEIGHTS["CD"], step=0.1, key="peee_w_cd",
                )
            with w_cols[1]:
                pe_weights["ND"] = st.number_input(
                    "ND Weight", min_value=WEIGHT_BOUNDS[0], max_value=WEIGHT_BOUNDS[1],
                    value=DEFAULT_WEIGHTS["ND"], step=0.1, key="peee_w_nd",
                )
            with w_cols[2]:
                pe_weights["AD"] = st.number_input(
                    "AD Weight", min_value=WEIGHT_BOUNDS[0], max_value=WEIGHT_BOUNDS[1],
                    value=DEFAULT_WEIGHTS["AD"], step=0.1, key="peee_w_ad",
                )
            with w_cols[3]:
                pe_weights["MD"] = st.number_input(
                    "MD Weight", min_value=WEIGHT_BOUNDS[0], max_value=WEIGHT_BOUNDS[1],
                    value=DEFAULT_WEIGHTS["MD"], step=0.1, key="peee_w_md",
                )
        st.warning(
            "Experimental coefficients are configurable simulation parameters and "
            "should not be interpreted as universal physiological constants."
        )

    recalculate_pe = st.button("Recalculate Perceived Error", use_container_width=True)
    if recalculate_pe:
        coordinator.set_error_model_context(
            model=pe_model, weights=pe_weights, network_condition=network_condition
        )
        coordinator.run_peee_pass()
        st.rerun()

    run_cycle = st.button("Run Communication Cycle", use_container_width=True)
    if run_cycle:
        st.session_state.dt_sim_time = st.session_state.get("dt_sim_time", 0.0) + config["time_step"]
        coordinator.set_error_model_context(
            model=pe_model, weights=pe_weights, network_condition=network_condition
        )
        coordinator.run_communication_cycle(simulation_timestamp=st.session_state.dt_sim_time)
        st.rerun()

    st.markdown("**Communication Log**")
    if coordinator.log:
        recent = coordinator.log[-200:]
        lines = [
            f"T={entry.timestamp:.2f} {entry.node_id} → Coordinator {entry.event}"
            for entry in reversed(recent)
        ]
        st.markdown(
            f'<div class="psdt-comm-log">{"<br>".join(lines)}</div>',
            unsafe_allow_html=True,
        )

        packet_ids = list(coordinator.packet_history.keys())
        selected_packet_id = st.selectbox(
            "Inspect a packet", list(reversed(packet_ids)), key="packet_inspector"
        )
        pssp = coordinator.packet_history[selected_packet_id]
        st.markdown(
            f"""
            <div class="psdt-card">
            <p style="margin:0 0 0.4rem 0;"><b>Packet ID</b><br>{pssp.packet_id}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Node</b><br>{pssp.node_id}</p>
            <p style="margin:0 0 0.4rem 0;"><b>Zone</b><br>{pssp.body_zone}</p>
            <p style="margin:0 0 0.8rem 0;"><b>Time</b><br>{pssp.simulation_timestamp} s</p>
            <hr style="margin:0.6rem 0;">
            <p style="margin:0 0 0.4rem 0;"><b>CD</b><br>{pssp.clock_drift_ms} ms</p>
            <p style="margin:0 0 0.4rem 0;"><b>ND</b><br>{pssp.network_delay_ms} ms</p>
            <p style="margin:0 0 0.4rem 0;"><b>AD</b><br>{pssp.actuator_driver_delay_ms} ms</p>
            <p style="margin:0 0 0.8rem 0;"><b>MD</b><br>{pssp.mechanical_startup_delay_ms} ms</p>
            <hr style="margin:0.6rem 0;">
            <p style="margin:0 0 0.4rem 0;"><b>Battery</b><br>{pssp.battery_percent} %</p>
            <p style="margin:0;"><b>State</b><br>{pssp.current_state}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="psdt-placeholder-box">No communication yet. '
            'Click &quot;Run Communication Cycle&quot; above.</div>',
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------
    # Data-flow visualization
    # -------------------------------------------------------------
    st.subheader("Synchronization Data Flow")

    chips_html = "".join(
        f'<span class="psdt-pipeline-chip">{name}<small>{sprint}</small></span>'
        for name, sprint in PIPELINE_STAGES
    )

    st.markdown(
        f"""
        <div class="psdt-card">
        <div class="psdt-flow-label">WEARABLE NODES</div>
        <div class="psdt-flow-arrow">↓ PSSP</div>
        <div class="psdt-flow-label">CENTRAL SYNCHRONIZATION COORDINATOR</div>
        <div class="psdt-flow-arrow">↓</div>
        <div style="text-align:center;">{chips_html}</div>
        <div class="psdt-flow-arrow">↓ PRAP</div>
        <div class="psdt-flow-label">WEARABLE NODES</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
