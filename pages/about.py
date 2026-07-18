import streamlit as st

st.markdown(
    '<div style="font-size:2rem; font-weight:800; color:#0B3D91; text-align:center;">About PSDT</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

SECTIONS = [
    "Introduction",
    "Patent Summary",
    "Architecture",
    "Novelty",
    "Prior Art",
    "Technology",
    "References",
]

for section in SECTIONS:
    st.markdown(f'<div class="psdt-section-heading">{section}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="psdt-placeholder-box" style="text-align:left; padding:1.5rem;">Content to be added.</div>',
        unsafe_allow_html=True,
    )
