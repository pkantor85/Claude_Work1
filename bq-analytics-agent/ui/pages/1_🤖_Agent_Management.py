"""
🤖 Agent Management — Create, update, view, and delete Data Agents.
"""

from __future__ import annotations

import streamlit as st

from src.agent_manager import (
    create_agent,
    delete_agent,
    get_agent,
    list_agents,
    update_agent,
)
from src.config_loader import (
    AgentConfig,
    AgentOptions,
    DatasourceConfig,
    GlobalConfig,
    PromptConfig,
)

st.set_page_config(page_title="Agent Management", page_icon="🤖", layout="wide")
st.title("🤖 Agent Management")

project_id = st.session_state.get("project_id", "")
location = st.session_state.get("location", "global")

if not project_id:
    st.warning("⚠️ Please set your GCP Project ID on the Home page.")
    st.stop()


# ── List Existing Agents ─────────────────────────────────

st.subheader("📋 Existing Agents")

if st.button("🔄 Refresh Agent List"):
    st.session_state.agents_cache = []

try:
    if not st.session_state.get("agents_cache"):
        with st.spinner("Loading agents…"):
            st.session_state.agents_cache = list_agents(project_id, location)

    agents = st.session_state.agents_cache

    if not agents:
        st.info("No agents found. Create one below.")
    else:
        for agent in agents:
            agent_id = agent.name.split("/")[-1]
            with st.expander(f"**{agent_id}** — {agent.description or 'No description'}"):
                st.code(agent.name, language="text")

                if hasattr(agent, "data_analytics_agent"):
                    ctx = agent.data_analytics_agent.published_context
                    if hasattr(ctx, "system_instruction"):
                        st.text_area(
                            "System Instruction",
                            value=ctx.system_instruction,
                            height=200,
                            key=f"instr_{agent_id}",
                            disabled=True,
                        )

                col_del, _ = st.columns([1, 4])
                with col_del:
                    if st.button(
                        "🗑️ Delete Agent",
                        key=f"del_{agent_id}",
                        type="secondary",
                    ):
                        with st.spinner("Deleting…"):
                            delete_agent(agent_id, project_id, location)
                        st.session_state.agents_cache = []
                        st.success(f"Agent '{agent_id}' deleted.")
                        st.rerun()
except Exception as e:
    st.error(f"Error loading agents: {e}")

st.divider()

# ── Create New Agent ──────────────────────────────────────

st.subheader("➕ Create New Agent")

with st.form("create_agent_form"):
    st.markdown("##### Agent Details")
    col1, col2 = st.columns(2)
    with col1:
        new_agent_id = st.text_input(
            "Agent ID *",
            placeholder="my_data_agent_v1",
            help="Unique identifier (lowercase, underscores, no spaces)",
        )
        new_display_name = st.text_input(
            "Display Name *",
            placeholder="My Data Agent",
        )
    with col2:
        new_agent_name = st.text_input(
            "Agent Persona Name *",
            placeholder="Data Assistant",
            help="Name used in the system instruction (e.g. 'Ordertake Agent')",
        )
        new_domain = st.text_input(
            "Domain *",
            placeholder="Automotive Order Take",
            help="Business domain description",
        )

    new_description = st.text_area(
        "Description",
        placeholder="Analyzes KPI data across markets…",
    )

    st.markdown("##### BigQuery Data Source")
    ds_col1, ds_col2, ds_col3 = st.columns(3)
    with ds_col1:
        ds_project = st.text_input(
            "BQ Project ID",
            value=project_id,
        )
    with ds_col2:
        ds_dataset = st.text_input(
            "Dataset ID *",
            placeholder="gold_business",
        )
    with ds_col3:
        ds_table = st.text_input(
            "Table ID *",
            placeholder="gold_kpi_unified",
        )

    st.markdown("##### System Instruction Source")
    instruction_source = st.radio(
        "How should the system instruction be generated?",
        ["Auto-generate from metadata JSON (GCS)", "Provide pre-built prompt (GCS path)"],
        horizontal=True,
    )
    if "Auto-generate" in instruction_source:
        metadata_path = st.text_input(
            "Metadata JSON path in GCS *",
            placeholder="4_business_glossary_and_KPI_Dataplex_vs_BigQuery.json",
        )
        prompt_path = None
    else:
        prompt_path = st.text_input(
            "Prompt text file path in GCS *",
            placeholder="prompts/ordertake_system_instruction.txt",
        )
        metadata_path = None

    gcs_bucket = st.text_input(
        "GCS Bucket Name *",
        placeholder="ordertake-datalake-gcp-pilot-landing",
    )

    st.markdown("##### Options")
    opt_col1, opt_col2 = st.columns(2)
    with opt_col1:
        python_enabled = st.checkbox("Enable Python Analysis", value=True)
    with opt_col2:
        stateful = st.checkbox("Stateful Chat", value=True)

    submitted = st.form_submit_button("🚀 Create Agent", type="primary")

    if submitted:
        # Validate
        missing = []
        if not new_agent_id:
            missing.append("Agent ID")
        if not new_display_name:
            missing.append("Display Name")
        if not ds_dataset:
            missing.append("Dataset ID")
        if not ds_table:
            missing.append("Table ID")
        if not gcs_bucket:
            missing.append("GCS Bucket")
        if not metadata_path and not prompt_path:
            missing.append("Metadata path or Prompt path")

        if missing:
            st.error(f"Missing required fields: {', '.join(missing)}")
        else:
            agent_cfg = AgentConfig(
                agent_id=new_agent_id,
                display_name=new_display_name,
                description=new_description,
                prompt_config=PromptConfig(
                    agent_name=new_agent_name or new_display_name,
                    domain=new_domain or "Data Analytics",
                    metadata_gcs_path=metadata_path,
                    prompt_gcs_path=prompt_path,
                ),
                datasources=[
                    DatasourceConfig(
                        project_id=ds_project or project_id,
                        dataset_id=ds_dataset,
                        table_id=ds_table,
                    )
                ],
                options=AgentOptions(
                    python_analysis_enabled=python_enabled,
                    stateful_chat=stateful,
                ),
            )
            global_cfg = GlobalConfig(
                project_id=project_id,
                location=location,
                gcs_bucket=gcs_bucket,
            )

            with st.spinner("Creating agent — this may take a moment…"):
                try:
                    result = create_agent(agent_cfg, global_cfg)
                    st.session_state.agents_cache = []
                    st.success(f"✅ Agent created: `{result.name}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error creating agent: {e}")
