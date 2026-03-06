"""
💬 Chat — Interactive conversation with BigQuery Data Agents.

Mimics the BigQuery Agent Console UI with:
- Agent & conversation selection
- Streaming response display (thoughts → SQL → data → charts)
- Multi-turn conversation support
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

from src.agent_manager import list_agents
from src.conversation_manager import (
    create_conversation,
    list_conversations,
    send_message_stateful,
)
from src.response_handler import AgentResponse, ResponseType, TextType
from ui.components.chat_message import render_agent_response
from ui.components.sql_display import render_sql

project_id = st.session_state.get("project_id", "")
location = st.session_state.get("location", "global")

if not project_id:
    st.warning("⚠️ Please set your GCP Project ID on the Home page.")
    st.stop()

# ── Sidebar: Agent & Conversation Selection ───────────────

with st.sidebar:
    st.subheader("💬 Chat Settings")

    # Load agents
    try:
        if not st.session_state.get("agents_cache"):
            st.session_state.agents_cache = list_agents(project_id, location)
        agents = st.session_state.agents_cache
    except Exception as e:
        st.error(f"Error loading agents: {e}")
        agents = []

    if not agents:
        st.warning("No agents found. Create one first.")
        st.stop()

    agent_options = {
        a.name.split("/")[-1]: a.description or a.name.split("/")[-1]
        for a in agents
    }
    selected_agent_id = st.selectbox(
        "Select Agent",
        options=list(agent_options.keys()),
        format_func=lambda x: f"{x} — {agent_options[x][:50]}",
    )

    st.divider()

    # Conversations for this agent
    st.markdown("**Conversations**")
    conv_key = f"convs_{selected_agent_id}"

    if st.button("🔄 Refresh Conversations"):
        st.session_state.pop(conv_key, None)

    try:
        if conv_key not in st.session_state:
            st.session_state[conv_key] = list_conversations(
                project_id, location
            )
        conversations = st.session_state[conv_key]
    except Exception:
        conversations = []

    conv_ids = ["(New Conversation)"] + [
        c.name.split("/")[-1] for c in conversations
    ]
    selected_conv = st.selectbox("Conversation", conv_ids)

    # Track active conversation
    if selected_conv == "(New Conversation)":
        active_conv_id = None
    else:
        active_conv_id = selected_conv

# ── Main Chat Area ────────────────────────────────────────

st.title("💬 Chat with Data Agent")
st.caption(f"Agent: **{selected_agent_id}** | Project: `{project_id}`")

# Initialize chat history for this agent
history_key = f"history_{selected_agent_id}_{active_conv_id or 'new'}"
if history_key not in st.session_state:
    st.session_state[history_key] = []

chat_history: list[dict[str, Any]] = st.session_state[history_key]

# ── Display existing messages ─────────────────────────────

for msg in chat_history:
    role = msg["role"]
    with st.chat_message(role, avatar="🧑‍💼" if role == "user" else "🤖"):
        if role == "user":
            st.markdown(msg["content"])
        else:
            # msg["content"] is a list of AgentResponse
            for resp in msg["content"]:
                render_agent_response(resp)

# ── Chat input ────────────────────────────────────────────

if question := st.chat_input("Ask a question about your data…"):
    # Display user message
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(question)
    chat_history.append({"role": "user", "content": question})

    # Create conversation if needed
    if active_conv_id is None:
        try:
            conv_id = f"conv_{uuid.uuid4().hex[:12]}"
            conv = create_conversation(
                agent_id=selected_agent_id,
                project_id=project_id,
                location=location,
                conversation_id=conv_id,
            )
            active_conv_id = conv_id
            # Clear conversation cache
            st.session_state.pop(conv_key, None)
        except Exception as e:
            st.error(f"Error creating conversation: {e}")
            st.stop()

    # Send message and stream response
    with st.chat_message("assistant", avatar="🤖"):
        response_placeholder = st.empty()
        collected_responses: list[AgentResponse] = []

        # Thought expander
        thought_container = st.expander("🧠 Agent Thinking…", expanded=False)
        final_container = st.container()

        try:
            responses = send_message_stateful(
                question=question,
                agent_id=selected_agent_id,
                conversation_id=active_conv_id,
                project_id=project_id,
                location=location,
                timeout=300,
            )
            collected_responses = responses

            # Render responses by type
            for resp in responses:
                if resp.response_type == ResponseType.TEXT:
                    if resp.text_type == TextType.THOUGHT:
                        with thought_container:
                            st.markdown(
                                resp.text,
                                unsafe_allow_html=False,
                            )
                    elif resp.text_type == TextType.FINAL_RESPONSE:
                        with final_container:
                            st.markdown(resp.text)
                    else:
                        with final_container:
                            st.markdown(resp.text)

                elif resp.response_type == ResponseType.DATA:
                    with final_container:
                        if resp.generated_sql:
                            render_sql(resp.generated_sql)
                        if resp.dataframe is not None and not resp.dataframe.empty:
                            st.dataframe(
                                resp.dataframe,
                                use_container_width=True,
                                hide_index=True,
                            )

                elif resp.response_type == ResponseType.CHART:
                    with final_container:
                        if resp.vega_config:
                            try:
                                import altair as alt

                                chart = alt.Chart.from_dict(resp.vega_config)
                                st.altair_chart(
                                    chart, use_container_width=True
                                )
                            except Exception as chart_err:
                                st.warning(
                                    f"Could not render chart: {chart_err}"
                                )
                                st.json(resp.vega_config)

                elif resp.response_type == ResponseType.SCHEMA:
                    with thought_container:
                        st.markdown("**Schema resolved:**")
                        for ds in resp.datasources:
                            st.json(ds)

        except Exception as e:
            st.error(f"Error: {e}")

    # Save to history
    chat_history.append(
        {"role": "assistant", "content": collected_responses}
    )
    st.session_state[history_key] = chat_history
