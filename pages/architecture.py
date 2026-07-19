import streamlit as st

st.title("Patent Architecture")

st.markdown(
    '<div style="text-align:center; font-weight:700; color:#0B3D91; font-size:1.15rem;">Coordinator</div>'
    '<div style="text-align:center; font-size:1.6rem; color:#94A3B8; line-height:1;">\u2193</div>',
    unsafe_allow_html=True,
)

MODULE_KEYS = ["DTCE", "PEEE", "PSME", "SCE", "ARAC"]
PLACEHOLDER = "(To be added)"

IMPLEMENTED_MODULES = {"DTCE", "PEEE", "PSME"}

MODULE_INFO = {
    "DTCE": {
        "purpose": "Computes a time-varying, body-zone-specific Dynamic Perceptual "
                    "Threshold PTz(t) for every active wearable node.",
        "input": "Body zone, vibration frequency, actuator type, user calibration, "
                 "motion state, environmental context",
        "output": "Dynamic Perceptual Threshold PTz(t) per node, with a full "
                  "auditable factor-by-factor breakdown",
        "equation": "PTz(t) = PTbase,z x Ff x Fa x UCF x Fm x Fe",
        "patent_section": PLACEHOLDER,
    },
}

if "selected_module" not in st.session_state:
    st.session_state.selected_module = None

module_cols = st.columns(5)
for col, key in zip(module_cols, MODULE_KEYS):
    with col:
        is_selected = st.session_state.selected_module == key
        card_class = "psdt-module-card psdt-module-card-selected" if is_selected else "psdt-module-card"
        status_text = "IMPLEMENTED &#10003;" if key in IMPLEMENTED_MODULES else "Not Implemented"
        status_color = "#16A34A" if key in IMPLEMENTED_MODULES else "#94A3B8"
        st.markdown(
            f'<div class="{card_class}">{key}<br>'
            f'<span style="font-size:0.7rem; font-weight:400; color:{status_color};">{status_text}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Select", key=f"select_{key}", use_container_width=True):
            st.session_state.selected_module = key
            st.rerun()

st.markdown(
    '<div style="text-align:center; font-size:1.6rem; color:#94A3B8; line-height:1; margin-top:1rem;">\u2193</div>'
    '<div style="text-align:center; font-weight:700; color:#0B3D91; font-size:1.15rem;">Distributed Nodes</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
st.subheader("Module Details")

selected = st.session_state.selected_module
if selected:
    info = MODULE_INFO.get(selected, {})
    st.markdown(
        f"""
        <div class="psdt-card">
            <h3 style="margin-top:0;">{selected}</h3>
            <p style="margin:0 0 0.7rem 0;"><b>Purpose</b><br>{info.get('purpose', PLACEHOLDER)}</p>
            <p style="margin:0 0 0.7rem 0;"><b>Input</b><br>{info.get('input', PLACEHOLDER)}</p>
            <p style="margin:0 0 0.7rem 0;"><b>Output</b><br>{info.get('output', PLACEHOLDER)}</p>
            <p style="margin:0 0 0.7rem 0;"><b>Equation</b><br>{info.get('equation', PLACEHOLDER)}</p>
            <p style="margin:0;"><b>Patent Section</b><br>{info.get('patent_section', PLACEHOLDER)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if selected == "DTCE":
        st.markdown(
            """
            <div class="psdt-card" style="text-align:center; margin-top:1rem;">
                <p style="margin:0 0 0.5rem 0; font-weight:600;">INPUTS</p>
                <p style="margin:0 0 0.7rem 0;">Body Zone &nbsp;|&nbsp; Frequency &nbsp;|&nbsp; Actuator
                &nbsp;|&nbsp; Calibration &nbsp;|&nbsp; Motion &nbsp;|&nbsp; Environment</p>
                <div style="font-size:1.4rem; color:#94A3B8;">&#8595;</div>
                <p style="margin:0.5rem 0; font-weight:700; color:#0B3D91;">
                Dynamic Threshold Characterization Engine</p>
                <div style="font-size:1.4rem; color:#94A3B8;">&#8595;</div>
                <p style="margin:0.5rem 0 0 0; font-weight:600;">OUTPUT</p>
                <p style="margin:0;">PTz(t) &ndash; Dynamic Perceptual Threshold</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="psdt-placeholder-box">Select a module to view details</div>',
        unsafe_allow_html=True,
    )
