import streamlit as st

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">Simulation</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

st.markdown('<div class="psdt-section-heading">Simulation Controls</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="psdt-card">', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.number_input("Nodes", min_value=1, max_value=50, value=6, disabled=True)
    with c2:
        st.select_slider("Simulation Speed", options=["0.5x", "1x", "1.5x", "2x"], value="1x", disabled=True)
    with c3:
        st.text_input("Seed", value="42", disabled=True)
    with c4:
        st.button("Run", disabled=True, use_container_width=True)
    with c5:
        st.button("Reset", disabled=True, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

main_col, side_col = st.columns([3, 1])

with main_col:
    st.markdown(
        '<div class="psdt-placeholder-box-lg">Simulation Area<br><span style="font-size:0.95rem; color:#CBD5E1;">(Coming in Sprint 3)</span></div>',
        unsafe_allow_html=True,
    )

with side_col:
    st.markdown('<div class="psdt-section-heading" style="margin-top:0;">Node Details</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="psdt-placeholder-box">Select a node</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

g1, g2, g3 = st.columns(3)
graph_labels = ["Synchronization Graph", "Energy Graph", "Communication Graph"]
for col, label in zip([g1, g2, g3], graph_labels):
    with col:
        st.markdown(
            f'<div class="psdt-placeholder-box">{label}<br><span style="font-size:0.85rem;">(Empty)</span></div>',
            unsafe_allow_html=True,
        )
