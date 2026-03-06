"""
sql_display — Render SQL queries with syntax highlighting.
"""

from __future__ import annotations

import streamlit as st


def render_sql(sql: str, title: str = "🔍 Generated SQL") -> None:
    """
    Display a SQL query with syntax highlighting in an expandable block.

    Parameters
    ----------
    sql:
        The SQL query string.
    title:
        Title for the expander.
    """
    if not sql or not sql.strip():
        return

    with st.expander(title, expanded=False):
        st.code(sql.strip(), language="sql")
