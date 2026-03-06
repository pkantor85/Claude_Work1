"""
data_table — Render tabular query results in a BigQuery Console-like style.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


def render_dataframe(
    df: pd.DataFrame,
    max_rows: int = 500,
    title: str = "📊 Query Results",
) -> None:
    """
    Display a Pandas DataFrame in a styled Streamlit table.

    Parameters
    ----------
    df:
        The data to display.
    max_rows:
        Maximum number of rows to render (prevents browser freeze).
    title:
        Optional title shown above the table.
    """
    if df.empty:
        st.info("No data returned.")
        return

    row_count = len(df)

    st.markdown(f"**{title}** ({row_count:,} row{'s' if row_count != 1 else ''})")

    # Truncate for display
    display_df = df.head(max_rows)
    if row_count > max_rows:
        st.warning(
            f"Showing first {max_rows:,} of {row_count:,} rows."
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    # Download button
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download CSV",
        data=csv,
        file_name="query_results.csv",
        mime="text/csv",
    )
