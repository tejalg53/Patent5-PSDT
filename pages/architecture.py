import streamlit as st

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">Patent Architecture</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    '<div style="text-align:center; font-weight:700; color:#0B3D91; font-size:1.15rem;">Coordinator</div>'
    '<div style="text-align:center; font-size:1.6rem; color:#94A3B8; line-height:1;">↓</div>',
    unsafe_allow_html=True,
)

MODULE_KEYS = ["DTCE", "PEEE", "PSME", "SCE", "ARAC"]

PLACEHOLDER = "(To be added)"

if "selected_module" not in st.session_state:
    st.session_state.selected_module = None

left_col, right_col = st.columns([2, 1])

with left_col:
    st.markdown("<br>", unsafe_allow_html=True)
    module_cols = st.columns(5)
    for col, key in zip(module_cols, MODULE_KEYS):
        with col:
            is_selected = st.session_state.selected_module == key
            card_class = "psdt-module-card psdt-module-card-selected" if is_selected else "psdt-module-card"
            st.markdown(
                f'<div class="{card_class}">{key}</div>',
                unsafe_allow_html=True,
            )
            if st.button("Select", key=f"select_{key}", use_container_width=True):
                st.session_state.selected_module = key
                st.rerun()

    st.markdown(
        '<div style="text-align:center; font-size:1.6rem; color:#94A3B8; line-height:1; margin-top:1rem;">↓</div>'
        '<div style="text-align:center; font-weight:700; color:#0B3D91; font-size:1.15rem;">Distributed Nodes</div>',
        unsafe_allow_html=True,
    )

with right_col:
    selected = st.session_state.selected_module
    if selected:
        st.markdown(
            f"""
            <div class="psdt-card">
                <div style="font-weight:800; color:#0B3D91; font-size:1.3rem; margin-bottom:0.8rem;">{selected}</div>
                <p style="margin:0 0 0.7rem 0;"><b>Purpose</b><br>{PLACEHOLDER}</p>
                <p style="margin:0 0 0.7rem 0;"><b>Input</b><br>{PLACEHOLDER}</p>
                <p style="margin:0 0 0.7rem 0;"><b>Output</b><br>{PLACEHOLDER}</p>
                <p style="margin:0 0 0.7rem 0;"><b>Equation</b><br>{PLACEHOLDER}</p>
                <p style="margin:0;"><b>Patent Section</b><br>{PLACEHOLDER}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="psdt-placeholder-box">Select a module to view details</div>',
            unsafe_allow_html=True,
        )
