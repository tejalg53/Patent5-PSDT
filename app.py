import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="PSDT - Perceptual Synchronization Digital Twin",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css():
    css_path = Path(__file__).parent / "styles" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


load_css()

home_page = st.Page("pages/home.py", title="Home", icon="🏠", default=True)
architecture_page = st.Page("pages/architecture.py", title="Patent Architecture", icon="🏗")
simulation_page = st.Page("pages/simulation.py", title="Simulation", icon="🧠")
analytics_page = st.Page("pages/analytics.py", title="Analytics", icon="📊")
comparison_page = st.Page("pages/comparison.py", title="Comparison", icon="⚖")
about_page = st.Page("pages/about.py", title="About", icon="ℹ")

pages = [
    home_page,
    architecture_page,
    simulation_page,
    analytics_page,
    comparison_page,
    about_page,
]

nav = st.navigation(pages, position="hidden")

with st.sidebar:
    st.markdown('<div class="psdt-sidebar-title">🧠 PSDT</div>', unsafe_allow_html=True)
    st.markdown("<hr style='margin:0.4rem 0 1rem 0;'>", unsafe_allow_html=True)
    for p in pages:
        st.page_link(p, label=f"{p.icon}  {p.title}", use_container_width=True)
    st.markdown("<hr style='margin:1.5rem 0 0.6rem 0;'>", unsafe_allow_html=True)
    st.markdown('<div class="psdt-sidebar-version">Version 1.0</div>', unsafe_allow_html=True)

nav.run()
