import streamlit as st
import pandas as pd

from config.resource_profiles import (
    FIXED_BASELINE_SYNC_INTERVAL_MS,
    FIXED_BASELINE_BEACON_INTERVAL_MS,
    FIXED_BASELINE_RADIO_WAKEUP_INTERVAL_MS,
    FIXED_BASELINE_TRANSMIT_POWER_PCT,
)

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">Comparison</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------------
# Sprint 9: Before ARAC (fixed, uniform resource profile) vs After ARAC
# (adaptive, per-node resource allocation driven by SCE state) - Sprint 9
# Deliverable 14.
# ---------------------------------------------------------------------
coordinator = st.session_state.get("dt_coordinator")
adaptive_nodes = (
    [n for n in coordinator.registry.values() if n.resource_status == "Adaptive"]
    if coordinator
    else []
)

if adaptive_nodes:
    avg_sync = sum(n.allocated_sync_interval_ms for n in adaptive_nodes) / len(adaptive_nodes)
    avg_beacon = sum(n.allocated_beacon_interval_ms for n in adaptive_nodes) / len(adaptive_nodes)
    avg_wakeup = sum(n.allocated_radio_wakeup_interval_ms for n in adaptive_nodes) / len(adaptive_nodes)
    avg_power = sum(n.allocated_transmit_power_pct for n in adaptive_nodes) / len(adaptive_nodes)
else:
    avg_sync = avg_beacon = avg_wakeup = avg_power = None

left_col, right_col = st.columns(2)

with left_col:
    st.markdown(
        f"""
        <div class="psdt-comparison-panel">
        <div style="font-weight:700; color:#0B3D91; font-size:1.2rem;">Uniform Synchronization</div>
        <p style="margin:1rem 0 0.3rem 0;"><b>Sync Interval</b><br>{FIXED_BASELINE_SYNC_INTERVAL_MS:.0f} ms (fixed)</p>
        <p style="margin:0 0 0.3rem 0;"><b>Beacon Interval</b><br>{FIXED_BASELINE_BEACON_INTERVAL_MS:.0f} ms (fixed)</p>
        <p style="margin:0 0 0.3rem 0;"><b>Radio Wake-up Interval</b><br>{FIXED_BASELINE_RADIO_WAKEUP_INTERVAL_MS:.0f} ms (fixed)</p>
        <p style="margin:0;"><b>Transmit Power</b><br>{FIXED_BASELINE_TRANSMIT_POWER_PCT:.0f}% (fixed)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_col:
    if adaptive_nodes:
        st.markdown(
            f"""
            <div class="psdt-comparison-panel">
            <div style="font-weight:700; color:#0B3D91; font-size:1.2rem;">PSM Synchronization</div>
            <p style="margin:1rem 0 0.3rem 0;"><b>Avg Sync Interval</b><br>{avg_sync:.1f} ms (adaptive, ARAC)</p>
            <p style="margin:0 0 0.3rem 0;"><b>Avg Beacon Interval</b><br>{avg_beacon:.1f} ms (adaptive, ARAC)</p>
            <p style="margin:0 0 0.3rem 0;"><b>Avg Radio Wake-up Interval</b><br>{avg_wakeup:.1f} ms (adaptive, ARAC)</p>
            <p style="margin:0;"><b>Avg Transmit Power</b><br>{avg_power:.1f}% (adaptive, ARAC)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="psdt-comparison-panel">
                <div style="font-weight:700; color:#0B3D91; font-size:1.2rem;">PSM Synchronization</div>
                <div style="color:#94A3B8; margin-top:2rem;">Run a communication cycle to see ARAC-adaptive resource averages.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="psdt-section-heading">Comparison Table</div>', unsafe_allow_html=True)

if adaptive_nodes:
    saving_pct = (
        (FIXED_BASELINE_TRANSMIT_POWER_PCT - avg_power) / FIXED_BASELINE_TRANSMIT_POWER_PCT * 100.0
        if FIXED_BASELINE_TRANSMIT_POWER_PCT
        else None
    )
    table = pd.DataFrame(
        {
            "Metric": [
                "Sync Interval (ms)",
                "Beacon Interval (ms)",
                "Radio Wake-up Interval (ms)",
                "Transmit Power (%)",
                "Estimated TX Power Saving (%)",
            ],
            "Uniform Synchronization": [
                FIXED_BASELINE_SYNC_INTERVAL_MS,
                FIXED_BASELINE_BEACON_INTERVAL_MS,
                FIXED_BASELINE_RADIO_WAKEUP_INTERVAL_MS,
                FIXED_BASELINE_TRANSMIT_POWER_PCT,
                0.0,
            ],
            "PSM Synchronization": [
                round(avg_sync, 1),
                round(avg_beacon, 1),
                round(avg_wakeup, 1),
                round(avg_power, 1),
                round(saving_pct, 1) if saving_pct is not None else None,
            ],
        }
    )
else:
    table = pd.DataFrame(columns=["Metric", "Uniform Synchronization", "PSM Synchronization"])

st.dataframe(table, use_container_width=True, hide_index=True)
st.caption(
    "Uniform Synchronization reflects a single fixed baseline configuration applied "
    "to every node before ARAC. PSM Synchronization reflects the average of each "
    "node's ARAC-adaptive resource allocation, driven by its SCE-classified state "
    "(Sprint 9 Deliverable 14). Estimated TX Power Saving is illustrative, derived "
    "from the simulation model rather than a hardware measurement."
)
