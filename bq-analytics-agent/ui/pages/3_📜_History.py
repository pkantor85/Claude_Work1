"""
📜 History — Browse and resume past conversations.
"""

from __future__ import annotations

import streamlit as st

from src.agent_manager import list_agents
from src.conversation_manager import (
    delete_conversation,
    list_conversations,
    list_messages,
)

st.set_page_config(page_title="Conversation History", page_icon="📜", layout="wide")
st.title("📜 Conversation History")

project_id = st.session_state.get("project_id", "")
location = st.session_state.get("location", "global")

if not project_id:
    st.warning("⚠️ Please set your GCP Project ID on the Home page.")
    st.stop()

# ── Load conversations ────────────────────────────────────

if st.button("🔄 Refresh"):
    st.session_state.pop("all_conversations", None)

try:
    if "all_conversations" not in st.session_state:
        with st.spinner("Loading conversations…"):
            st.session_state.all_conversations = list_conversations(
                project_id, location
            )
    conversations = st.session_state.all_conversations
except Exception as e:
    st.error(f"Error loading conversations: {e}")
    conversations = []

if not conversations:
    st.info("No conversations found. Start a chat first.")
    st.stop()

# ── Display conversations ─────────────────────────────────

st.markdown(f"**{len(conversations)}** conversation(s) found.")

for conv in conversations:
    conv_id = conv.name.split("/")[-1]
    agents_str = ", ".join(
        a.split("/")[-1] for a in getattr(conv, "agents", [])
    )

    with st.expander(f"🗨️ **{conv_id}** — Agents: {agents_str or 'N/A'}"):
        st.code(conv.name, language="text")

        # Load messages
        if st.button(f"📨 Load Messages", key=f"load_{conv_id}"):
            try:
                with st.spinner("Loading messages…"):
                    messages = list_messages(
                        conversation_id=conv_id,
                        project_id=project_id,
                        location=location,
                    )
                if not messages:
                    st.info("No messages in this conversation.")
                else:
                    for msg in messages:
                        if hasattr(msg, "user_message") and msg.user_message:
                            st.chat_message("user", avatar="🧑‍💼").markdown(
                                getattr(msg.user_message, "text", "")
                            )
                        elif hasattr(msg, "system_message") and msg.system_message:
                            sm = msg.system_message
                            if hasattr(sm, "text") and sm.text:
                                parts = list(getattr(sm.text, "parts", []))
                                text = "".join(parts)
                                st.chat_message(
                                    "assistant", avatar="🤖"
                                ).markdown(text)
            except Exception as e:
                st.error(f"Error loading messages: {e}")

        # Delete
        if st.button(
            "🗑️ Delete Conversation",
            key=f"del_conv_{conv_id}",
            type="secondary",
        ):
            try:
                delete_conversation(conv_id, project_id, location)
                st.session_state.pop("all_conversations", None)
                st.success(f"Conversation '{conv_id}' deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting conversation: {e}")
