"""Streamlit chat UI for BigQuery Conversational Analytics agents.

Mimics the look and feel of the BigQuery Console agent chat interface:
  - Left sidebar with agent selection and metadata
  - Main area with streaming chat messages
  - Expandable SQL, data tables, and Vega-Lite charts
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import streamlit as st

# Ensure project root is on the path so local imports work when
# Streamlit is launched from within the ``ui/`` directory.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from agents.provisioner import AgentProvisioner  # noqa: E402
from chat.service import ChatService, ChatSession  # noqa: E402
from config.loader import load_config_from_file, load_config_from_gcs  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BigQuery Data Agent",
    page_icon=":material/query_stats:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS — approximate the BQ console look
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Header bar */
    .bq-header {
        background-color: #1a73e8;
        color: white;
        padding: 12px 24px;
        font-size: 18px;
        font-weight: 500;
        border-radius: 8px 8px 0 0;
        margin-bottom: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .bq-header-icon {
        font-size: 22px;
    }
    /* Chat container */
    .chat-container {
        border: 1px solid #dadce0;
        border-radius: 0 0 8px 8px;
        padding: 16px;
        min-height: 400px;
        background: #fff;
    }
    /* Agent info card */
    .agent-card {
        background: #f8f9fa;
        border: 1px solid #dadce0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .agent-card h3 {
        margin: 0 0 4px 0;
        color: #202124;
    }
    .agent-card p {
        margin: 0;
        color: #5f6368;
        font-size: 14px;
    }
    /* Knowledge source chip */
    .ks-chip {
        display: inline-block;
        background: #e8f0fe;
        color: #1a73e8;
        border-radius: 16px;
        padding: 4px 12px;
        font-size: 13px;
        margin: 4px 2px;
    }
    /* Glossary term row */
    .glossary-row {
        padding: 6px 0;
        border-bottom: 1px solid #f1f3f4;
        font-size: 13px;
    }
    .glossary-term {
        font-weight: 500;
        color: #1a73e8;
    }
    .glossary-def {
        color: #5f6368;
    }
    /* Thinking indicator */
    .thinking {
        color: #5f6368;
        font-style: italic;
        font-size: 13px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "agents_list" not in st.session_state:
    st.session_state.agents_list = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "config" not in st.session_state:
    st.session_state.config = None
if "metadata_cache" not in st.session_state:
    st.session_state.metadata_cache = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_agent_name(project_id: str, location: str, agent_id: str) -> str:
    return f"projects/{project_id}/locations/{location}/dataAgents/{agent_id}"


def _load_agents_from_config() -> None:
    """Load agent configs into session state."""
    config_source = st.session_state.get("config_source", "local")
    try:
        if config_source == "gcs":
            bucket = st.session_state.get("gcs_bucket", "")
            path = st.session_state.get("gcs_path", "")
            project = st.session_state.get("gcp_project", "")
            cfg = load_config_from_gcs(bucket, path, project)
        else:
            local_path = st.session_state.get("local_config_path", "")
            cfg = load_config_from_file(local_path)

        st.session_state.config = cfg
        st.session_state.agents_list = [
            {"agent_id": a.agent_id, "display_name": a.display_name, "description": a.description}
            for a in cfg.agents
        ]
    except Exception as exc:
        st.error(f"Failed to load config: {exc}")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### BigQuery Agent Console")

    # --- Config source ---
    st.markdown("---")
    st.markdown("**Agent Configuration**")
    config_source = st.radio(
        "Config source",
        ["local", "gcs"],
        horizontal=True,
        key="config_source",
    )
    if config_source == "gcs":
        st.text_input("GCP Project", key="gcp_project")
        st.text_input("GCS Bucket", key="gcs_bucket")
        st.text_input("Config object path", key="gcs_path", value="agents_config.json")
    else:
        st.text_input(
            "Local config path",
            key="local_config_path",
            value=str(Path(_PROJECT_ROOT) / "sample_configs" / "agents_config.json"),
        )
    if st.button("Load agents"):
        _load_agents_from_config()

    # --- Agent selector ---
    if st.session_state.agents_list:
        st.markdown("---")
        agent_names = [a["display_name"] for a in st.session_state.agents_list]
        selected_idx = st.selectbox(
            "Select Agent",
            range(len(agent_names)),
            format_func=lambda i: agent_names[i],
            key="selected_agent_idx",
        )
        selected_agent = st.session_state.agents_list[selected_idx]

        # Agent info card
        st.markdown(
            f"""
            <div class="agent-card">
                <h3>{selected_agent['display_name']}</h3>
                <p>{selected_agent['description']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Knowledge sources
        cfg = st.session_state.config
        if cfg:
            agent_cfg = cfg.agents[selected_idx]
            st.markdown("**Knowledge sources**")
            for ds in agent_cfg.datasources:
                label = f"{ds.project_id}.{ds.dataset_id}.{ds.table_id}"
                st.markdown(f'<span class="ks-chip">{label}</span>', unsafe_allow_html=True)

            # Glossary terms
            if agent_cfg.agent_id in st.session_state.metadata_cache:
                meta = st.session_state.metadata_cache[agent_cfg.agent_id]
                terms = meta.get("dataplex_business_glossary", {}).get("terms", [])
                if terms:
                    with st.expander(f"Glossary ({len(terms)} terms)"):
                        for t in terms:
                            st.markdown(
                                f'<div class="glossary-row">'
                                f'<span class="glossary-term">{t["business_term"]}</span> — '
                                f'<span class="glossary-def">{t.get("definition", "")}</span>'
                                f"</div>",
                                unsafe_allow_html=True,
                            )

        # New conversation button
        st.markdown("---")
        if st.button("New conversation"):
            st.session_state.messages = []
            st.session_state.chat_session = None

# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="bq-header">'
    '<span class="bq-header-icon">&#x1F4CA;</span> BigQuery Data Agent'
    "</div>",
    unsafe_allow_html=True,
)

# Render conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("sql"):
            with st.expander("SQL Query"):
                st.code(msg["sql"], language="sql")
        if msg.get("chart_spec"):
            try:
                st.vega_lite_chart(json.loads(msg["chart_spec"]))
            except Exception:
                pass
        st.markdown(msg.get("content", ""))

# Chat input
if prompt := st.chat_input("Ask a question"):
    if not st.session_state.agents_list:
        st.warning("Load an agent configuration first.")
    else:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Ensure chat session exists
        cfg = st.session_state.config
        selected_idx = st.session_state.get("selected_agent_idx", 0)
        agent_cfg = cfg.agents[selected_idx]
        agent_name = _get_agent_name(cfg.project_id, cfg.location, agent_cfg.agent_id)

        if st.session_state.chat_session is None:
            svc = ChatService(cfg.project_id, cfg.location)
            session = ChatSession(svc, agent_name)
            session.start()
            st.session_state.chat_session = session

        session: ChatSession = st.session_state.chat_session

        # Stream response
        with st.chat_message("assistant"):
            answer_parts: list[str] = []
            sql_parts: list[str] = []
            chart_spec: str | None = None
            status_placeholder = st.empty()

            try:
                for chunk in session.ask(prompt):
                    if chunk.kind == "thought":
                        status_placeholder.markdown(
                            f'<p class="thinking">Thinking: {chunk.content}</p>',
                            unsafe_allow_html=True,
                        )
                    elif chunk.kind == "progress":
                        status_placeholder.markdown(
                            f'<p class="thinking">{chunk.content}</p>',
                            unsafe_allow_html=True,
                        )
                    elif chunk.kind == "query":
                        sql_parts.append(str(chunk.content))
                    elif chunk.kind == "chart":
                        chart_spec = str(chunk.content)
                    elif chunk.kind in ("answer", "text"):
                        answer_parts.append(str(chunk.content))
                    elif chunk.kind == "error":
                        st.error(chunk.content)

                # Clear thinking indicator
                status_placeholder.empty()

                # Show SQL
                sql_text = "\n".join(sql_parts) if sql_parts else None
                if sql_text:
                    with st.expander("SQL Query"):
                        st.code(sql_text, language="sql")

                # Show chart
                if chart_spec:
                    try:
                        st.vega_lite_chart(json.loads(chart_spec))
                    except Exception:
                        pass

                # Show answer
                answer_text = "\n".join(answer_parts) if answer_parts else "No response."
                st.markdown(answer_text)

            except Exception as exc:
                st.error(f"Chat error: {exc}")
                answer_text = f"Error: {exc}"
                sql_text = None
                chart_spec = None

        # Record in history
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer_text,
                "sql": sql_text,
                "chart_spec": chart_spec,
            }
        )

# Footer hint
if not st.session_state.messages:
    st.markdown(
        """
        <div style="text-align:center; color:#5f6368; margin-top:80px;">
            <p style="font-size:16px;">Ask a question about your data</p>
            <p style="font-size:13px;">
                View best practices for better answers.
                The responses from Conversational Analytics in BigQuery may not be complete or accurate.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
