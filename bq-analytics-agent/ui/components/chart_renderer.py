"""
chart_renderer — Render Vega-Lite chart specifications from the CA API.

The CA API returns chart responses as Vega-Lite JSON configs.
This module uses Altair to render them in Streamlit.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import streamlit as st


def render_chart(
    vega_config: Optional[dict[str, Any]],
    title: str = "📈 Chart",
) -> None:
    """
    Render a Vega-Lite specification as an Altair chart in Streamlit.

    Parameters
    ----------
    vega_config:
        Vega-Lite spec dictionary returned by the CA API.
    title:
        Optional title above the chart.
    """
    if not vega_config:
        return

    st.markdown(f"**{title}**")

    try:
        import altair as alt

        chart = alt.Chart.from_dict(vega_config)
        st.altair_chart(chart, use_container_width=True)
    except ImportError:
        st.warning("Altair is not installed. Showing raw chart spec.")
        st.json(vega_config)
    except Exception as e:
        st.warning(f"Could not render chart: {e}")
        with st.expander("Raw Vega-Lite Spec"):
            st.json(vega_config)
