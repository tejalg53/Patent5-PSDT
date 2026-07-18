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
from core.constants import ZONE_ORDER

st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Dynamic Perceptual Threshold by Body Zone")

coordinator = st.session_state.get("dt_coordinator")
if coordinator and coordinator.dtce_audit:
    pt_rows = [
        {"Body Zone": audit.body_zone, "Dynamic PT (ms)": audit.dynamic_pt_ms}
        for audit in coordinator.dtce_audit.values()
    ]
    pt_df = pd.DataFrame(pt_rows)

    mean_by_zone = (
        pt_df.groupby("Body Zone")["Dynamic PT (ms)"]
        .mean()
        .reindex([z for z in ZONE_ORDER if z in pt_df["Body Zone"].unique()])
    )
    st.bar_chart(mean_by_zone)
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
