"""
chat_message — Render individual agent responses in the Streamlit chat.

Handles the different response types:
- Text (thoughts, progress, final answer)
- Data tables
- Charts (Vega-Lite / Altair)
- Schema info
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.response_handler import AgentResponse, ResponseType, TextType
from ui.components.data_table import render_dataframe
from ui.components.chart_renderer import render_chart
from ui.components.sql_display import render_sql


def render_agent_response(resp: AgentResponse) -> None:
    """Render a single :class:`AgentResponse` in the Streamlit UI."""

    if resp.response_type == ResponseType.TEXT:
        _render_text(resp)
    elif resp.response_type == ResponseType.DATA:
        _render_data(resp)
    elif resp.response_type == ResponseType.CHART:
        render_chart(resp.vega_config)
    elif resp.response_type == ResponseType.SCHEMA:
        _render_schema(resp)


def _render_text(resp: AgentResponse) -> None:
    """Render a text response based on its TextType."""
    if resp.text_type == TextType.THOUGHT:
        with st.expander("🧠 Agent Thought", expanded=False):
            st.markdown(resp.text, unsafe_allow_html=False)
    elif resp.text_type == TextType.PROGRESS:
        st.info(f"⏳ {resp.text}")
    elif resp.text_type == TextType.FINAL_RESPONSE:
        st.markdown(resp.text)
    else:
        st.markdown(resp.text)


def _render_data(resp: AgentResponse) -> None:
    """Render SQL + tabular data."""
    if resp.generated_sql:
        render_sql(resp.generated_sql)
    if resp.dataframe is not None and not resp.dataframe.empty:
        render_dataframe(resp.dataframe)


def _render_schema(resp: AgentResponse) -> None:
    """Render resolved schema information."""
    with st.expander("📊 Resolved Schema", expanded=False):
        for ds in resp.datasources:
            st.json(ds)
