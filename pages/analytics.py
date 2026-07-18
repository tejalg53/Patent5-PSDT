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
