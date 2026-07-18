import streamlit as st

st.markdown(
    """
    <div style="text-align:center; padding-top: 1rem;">
        <div style="font-size:2.8rem; font-weight:800; color:#0B3D91;">🧠 PSDT</div>
        <div style="font-size:1.5rem; font-weight:700; color:#0B3D91; margin-top:0.3rem;">
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

st.markdown(
    """
    <div class="psdt-hero-card">
        <p style="font-size:1.05rem; color:#334155; line-height:1.7; margin:0;">
        The PSDT platform demonstrates the operation of the Perceptual Synchronization Margin
        based Adaptive Synchronization Framework proposed in Patent 5. The platform models
        distributed wearable nodes, adaptive synchronization, communication overhead, energy
        consumption, and synchronization behavior.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="psdt-nav-card">
            <div style="font-size:2rem;">🚀</div>
            <div style="font-weight:700; color:#0B3D91; font-size:1.1rem; margin-top:0.5rem;">Start Simulation</div>
            <div style="color:#64748B; margin-top:0.3rem;">Launch the Digital Twin</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Open Simulation", key="home_sim_btn", use_container_width=True):
        st.switch_page("pages/simulation.py")

with col2:
    st.markdown(
        """
        <div class="psdt-nav-card">
            <div style="font-size:2rem;">🏗</div>
            <div style="font-weight:700; color:#0B3D91; font-size:1.1rem; margin-top:0.5rem;">Patent Architecture</div>
            <div style="color:#64748B; margin-top:0.3rem;">Understand the complete invention</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Open Architecture", key="home_arch_btn", use_container_width=True):
        st.switch_page("pages/architecture.py")

with col3:
    st.markdown(
        """
        <div class="psdt-nav-card">
            <div style="font-size:2rem;">📄</div>
            <div style="font-weight:700; color:#0B3D91; font-size:1.1rem; margin-top:0.5rem;">Documentation</div>
            <div style="color:#64748B; margin-top:0.3rem;">Patent summary and methodology</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Open Documentation", key="home_doc_btn", use_container_width=True):
        st.switch_page("pages/about.py")

st.markdown("<br>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
stats = [
    ("TRL", "2"),
    ("Patent", "Verified"),
    ("Version", "1.0"),
    ("Platform", "Browser Based"),
]
for col, (label, value) in zip([c1, c2, c3, c4], stats):
    with col:
        st.markdown(
            f"""
            <div class="psdt-stat-card">
                <div class="psdt-stat-label">{label}</div>
                <div class="psdt-stat-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
