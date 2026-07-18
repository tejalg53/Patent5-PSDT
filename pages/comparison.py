import streamlit as st
import pandas as pd

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">Comparison</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

left_col, right_col = st.columns(2)

with left_col:
    st.markdown(
        """
        <div class="psdt-comparison-panel">
            <div style="font-weight:700; color:#0B3D91; font-size:1.2rem;">Uniform Synchronization</div>
            <div style="color:#94A3B8; margin-top:2rem;">Placeholder</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right_col:
    st.markdown(
        """
        <div class="psdt-comparison-panel">
            <div style="font-weight:700; color:#0B3D91; font-size:1.2rem;">PSM Synchronization</div>
            <div style="color:#94A3B8; margin-top:2rem;">Placeholder</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="psdt-section-heading">Comparison Table</div>', unsafe_allow_html=True)

empty_table = pd.DataFrame(
    columns=["Metric", "Uniform Synchronization", "PSM Synchronization"]
)
st.dataframe(empty_table, use_container_width=True, hide_index=True)
