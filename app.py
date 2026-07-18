import streamlit as st

st.set_page_config(
    page_title="PSDT - Perceptual Synchronization Digital Twin",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp {
    background-color: #ffffff;
}
h1, h2, h3 {
    color: #0a2540;
}
.psdt-architecture-card {
    background-color: #f5f6f8;
    border-radius: 18px;
    padding: 4rem 2rem;
    text-align: center;
    margin-bottom: 2rem;
}
.psdt-status-card {
    background-color: #f5f6f8;
    border-radius: 14px;
    padding: 1.5rem;
    text-align: center;
}
.psdt-status-label {
    color: #0a2540;
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.psdt-status-value {
    color: #333333;
    font-size: 1.15rem;
    margin-top: 0.4rem;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Navigation")
    st.radio(
        "Navigation",
        ["Home", "Patent Architecture", "Simulation", "Results", "About"],
        label_visibility="collapsed",
    )

st.markdown(
    """
    <div style="text-align:center; padding-top: 1rem;">
        <div style="font-size:3.2rem; font-weight:800; color:#0a2540; letter-spacing:0.05em;">PSDT</div>
        <div style="font-size:1.6rem; font-weight:600; color:#0a2540; margin-top:0.3rem;">
            Perceptual Synchronization Digital Twin
        </div>
        <div style="font-size:1.05rem; color:#5a6472; margin-top:0.5rem;">
            Digital Twin Platform for Adaptive Synchronization in Distributed Wearable Haptic Systems
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<br>", unsafe_allow_html=True)

st.info(
    "The PSDT platform provides a browser-based digital twin for demonstrating the patented "
    "Perceptual Synchronization Margin (PSM)-based adaptive synchronization framework. It models "
    "distributed wearable haptic nodes, synchronization behavior, perceptual threshold estimation, "
    "synchronization state transitions, adaptive resource allocation, and communication overhead in "
    "a configurable virtual environment."
)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="psdt-architecture-card">
        <div style="font-size:1.3rem; font-weight:700; color:#0a2540;">Figure 2</div>
        <div style="font-size:1.1rem; color:#333333; margin-top:0.3rem;">Overall Patent Architecture</div>
        <div style="font-size:1rem; color:#9aa3ad; margin-top:1.5rem;">(To be added)</div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    st.button("Start Simulation", use_container_width=True)
with col2:
    st.button("View Patent Architecture", use_container_width=True)
with col3:
    st.button("About PSDT", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

status_items = [
    ("TRL", "2"),
    ("Patent", "Verified Architecture"),
    ("Version", "1.0"),
    ("Platform", "Browser-Based"),
]

for col, (label, value) in zip([c1, c2, c3, c4], status_items):
    with col:
        st.markdown(
            f"""
            <div class="psdt-status-card">
                <div class="psdt-status-label">{label}</div>
                <div class="psdt-status-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
