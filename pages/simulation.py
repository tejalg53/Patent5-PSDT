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

st.title("Simulation")

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
