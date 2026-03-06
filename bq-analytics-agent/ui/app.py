"""
BigQuery Data Analytics Agent — Streamlit Application Entry Point.

Provides a multi-page app with:
  1. 🤖 Agent Management  — Create / Update / Delete data agents
  2. 💬 Chat              — Ask natural language questions
  3. 📜 History           — Browse past conversations
"""

from __future__ import annotations

import streamlit as st

# ── Page Configuration ────────────────────────────────────

st.set_page_config(
    page_title="BQ Data Analytics Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load custom CSS ───────────────────────────────────────

_CSS_PATH = "ui/styles/custom.css"
try:
    with open(_CSS_PATH) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ── Sidebar branding ─────────────────────────────────────

with st.sidebar:
    st.image(
        "https://www.gstatic.com/pantheon/images/welcome/supercloud.svg",
        width=40,
    )
    st.title("BQ Data Agent")
    st.caption("Powered by Google Cloud Conversational Analytics API")
    st.divider()

# ── Session state defaults ────────────────────────────────

if "project_id" not in st.session_state:
    try:
        st.session_state.project_id = st.secrets["cloud"]["project_id"]
    except Exception:
        st.session_state.project_id = ""

if "location" not in st.session_state:
    try:
        st.session_state.location = st.secrets["cloud"]["location"]
    except Exception:
        st.session_state.location = "global"

if "agents_cache" not in st.session_state:
    st.session_state.agents_cache = []

if "conversations" not in st.session_state:
    st.session_state.conversations = {}

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Landing page ──────────────────────────────────────────

st.title("🤖 BigQuery Data Analytics Agent")
st.markdown(
    """
    Welcome to the **BigQuery Data Analytics Agent** system.
    This application lets you create domain-specific data agents
    that answer natural language questions against BigQuery datasets.

    ### Getting Started

    1. **Configure** your GCP project ID in the sidebar settings below.
    2. Go to **🤖 Agent Management** to create or manage agents.
    3. Go to **💬 Chat** to start asking questions about your data.
    4. Go to **📜 History** to browse past conversations.

    ---
    """
)

# ── Quick settings ────────────────────────────────────────

with st.expander("⚙️ Project Settings", expanded=not st.session_state.project_id):
    col1, col2 = st.columns(2)
    with col1:
        project_id = st.text_input(
            "GCP Project ID",
            value=st.session_state.project_id,
            key="settings_project_id",
        )
    with col2:
        location = st.text_input(
            "Location",
            value=st.session_state.location,
            key="settings_location",
        )
    if st.button("Save Settings"):
        st.session_state.project_id = project_id
        st.session_state.location = location
        st.success("Settings saved!")
        st.rerun()

if not st.session_state.project_id:
    st.warning("⚠️ Please configure your GCP Project ID above to get started.")
