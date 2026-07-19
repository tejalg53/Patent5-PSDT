import streamlit as st

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">Analytics</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

cards = [
    ("\U0001F4E6", "Packets"),
    ("\U0001F50B", "Battery"),
    ("\u26A1", "Energy"),
    ("\U0001F4E1", "Communication"),
    ("\U0001F9ED", "Node States"),
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

    st.markdown("###### Threshold\u2013Error Diagnostic View")
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
            'the Threshold\u2013Error Diagnostic View.</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="psdt-placeholder-box">Initialize the Digital Twin and run a '
        'communication cycle on the Simulation page to populate Perceived Error '
        'analytics.</div>',
        unsafe_allow_html=True,
    )
