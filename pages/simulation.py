import streamlit as st
import pandas as pd

from core.constants import NODE_COUNT_OPTIONS, ZONE_ORDER
from core.node_factory import generate_nodes

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
    st.session_state.dt_nodes = generate_nodes(int(num_nodes), seed=int(seed))
    st.session_state.dt_config = {
        "num_nodes": int(num_nodes),
        "seed": int(seed),
        "duration": int(duration),
        "time_step": int(time_step),
    }

nodes = st.session_state.get("dt_nodes")
config = st.session_state.get("dt_config")

if not nodes:
    st.markdown(
        '<div class="psdt-placeholder-box-lg">Configure the parameters above and click '
        '&quot;Initialize Digital Twin&quot; to generate the wearable node network.</div>',
        unsafe_allow_html=True,
    )
else:
    st.caption(
        f"Active network: {config['num_nodes']} nodes  |  seed {config['seed']}  |  "
        f"duration {config['duration']}s  |  step {config['time_step']}s"
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
        dots = " ".join(["\u25cf"] * count) if count else "\u2014"
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
                <p style="margin:0 0 0.4rem 0;"><b>PT</b><br>{fmt(selected_node.perceptual_threshold)}</p>
                <p style="margin:0 0 0.4rem 0;"><b>PE</b><br>{fmt(selected_node.perceived_error)}</p>
                <p style="margin:0 0 0.4rem 0;"><b>PSM</b><br>{fmt(selected_node.psm)}</p>
                <p style="margin:0;"><b>State</b><br>{selected_node.sync_state}</p>
            </div>
            """,
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
                "Battery (%)": n.battery_level,
                "State": n.sync_state,
            }
            for n in nodes
            if n.body_zone in zone_filter
        ]

        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
