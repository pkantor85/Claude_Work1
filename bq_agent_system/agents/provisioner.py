"""Provision CA API data agents from configuration."""

from __future__ import annotations

import logging
from typing import Any

from google.api_core import exceptions as api_exceptions
from google.cloud import geminidataanalytics

from config.schema import AgentConfig, AgentsConfig, DatasourceConfig
from prompts.generator import generate_llm_system_prompt

logger = logging.getLogger(__name__)


class AgentProvisioner:
    """Creates, updates, and deletes Conversational Analytics data agents."""

    def __init__(self, project_id: str | None = None, location: str = "global"):
        self.project_id = project_id
        self.location = location
        self.client = geminidataanalytics.DataAgentServiceClient()
        self._parent = f"projects/{project_id}/locations/{location}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def provision_agent(
        self,
        agent_cfg: AgentConfig,
        metadata: dict[str, Any],
    ) -> geminidataanalytics.DataAgent:
        """Create or update a single CA API agent.

        If an agent with the same ID already exists it will be updated
        with the new configuration. Otherwise a new agent is created.

        Args:
            agent_cfg: Validated agent configuration.
            metadata: Parsed metadata JSON for prompt generation.

        Returns:
            The created or updated DataAgent resource.
        """
        system_prompt = generate_llm_system_prompt(
            metadata,
            agent_name=agent_cfg.prompt_settings.agent_name,
            domain=agent_cfg.prompt_settings.domain,
        )

        agent_name = f"{self._parent}/dataAgents/{agent_cfg.agent_id}"

        # Check for existing agent
        try:
            existing = self.client.get_data_agent(name=agent_name)
            logger.info("Agent %s exists — updating.", agent_cfg.agent_id)
            return self._update_agent(existing, agent_cfg, metadata, system_prompt)
        except api_exceptions.NotFound:
            logger.info("Creating new agent %s.", agent_cfg.agent_id)
            return self._create_agent(agent_cfg, metadata, system_prompt)

    def provision_all(
        self,
        config: AgentsConfig,
        metadata_map: dict[str, dict[str, Any]],
    ) -> list[geminidataanalytics.DataAgent]:
        """Provision all agents defined in the config.

        Args:
            config: Top-level agents configuration.
            metadata_map: Mapping of ``agent_id`` to its parsed metadata dict.

        Returns:
            List of created/updated DataAgent resources.
        """
        results = []
        for agent_cfg in config.agents:
            metadata = metadata_map[agent_cfg.agent_id]
            agent = self.provision_agent(agent_cfg, metadata)
            results.append(agent)
        return results

    def list_agents(self) -> list[geminidataanalytics.DataAgent]:
        """List all data agents in the configured project/location."""
        request = geminidataanalytics.ListDataAgentsRequest(parent=self._parent)
        return list(self.client.list_data_agents(request=request))

    def delete_agent(self, agent_id: str) -> None:
        """Delete an agent by ID."""
        name = f"{self._parent}/dataAgents/{agent_id}"
        request = geminidataanalytics.DeleteDataAgentRequest(name=name)
        self.client.delete_data_agent(request=request)
        logger.info("Deleted agent %s.", agent_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_agent(
        self,
        agent_cfg: AgentConfig,
        metadata: dict[str, Any],
        system_prompt: str,
    ) -> geminidataanalytics.DataAgent:
        """Create a new CA API data agent."""
        context = self._build_context(agent_cfg, metadata, system_prompt)

        data_agent = geminidataanalytics.DataAgent()
        data_agent.display_name = agent_cfg.display_name
        data_agent.data_analytics_agent = geminidataanalytics.DataAnalyticsAgent()
        data_agent.data_analytics_agent.published_context = context

        request = geminidataanalytics.CreateDataAgentRequest(
            parent=self._parent,
            data_agent_id=agent_cfg.agent_id,
            data_agent=data_agent,
        )
        response = self.client.create_data_agent(request=request)
        logger.info("Created agent: %s", response.name)
        return response

    def _update_agent(
        self,
        existing: geminidataanalytics.DataAgent,
        agent_cfg: AgentConfig,
        metadata: dict[str, Any],
        system_prompt: str,
    ) -> geminidataanalytics.DataAgent:
        """Update an existing CA API data agent."""
        context = self._build_context(agent_cfg, metadata, system_prompt)
        existing.display_name = agent_cfg.display_name
        existing.data_analytics_agent.published_context = context

        request = geminidataanalytics.UpdateDataAgentRequest(data_agent=existing)
        response = self.client.update_data_agent(request=request)
        logger.info("Updated agent: %s", response.name)
        return response

    def _build_context(
        self,
        agent_cfg: AgentConfig,
        metadata: dict[str, Any],
        system_prompt: str,
    ) -> geminidataanalytics.Context:
        """Build the CA API Context object from config + metadata."""
        # Build BigQuery table references with schema
        bq_refs = []
        tech_meta = metadata.get("bigquery_technical_metadata", {})
        columns = tech_meta.get("columns", {})

        for ds in agent_cfg.datasources:
            bq_ref = self._build_bq_reference(ds, tech_meta, columns)
            bq_refs.append(bq_ref)

        # Datasource references
        datasource_refs = geminidataanalytics.DatasourceReferences()
        datasource_refs.bq = geminidataanalytics.BigQueryTableReferences()
        datasource_refs.bq.table_references = bq_refs

        # Context
        context = geminidataanalytics.Context()
        context.system_instruction = system_prompt
        context.datasource_references = datasource_refs

        return context

    @staticmethod
    def _build_bq_reference(
        ds: DatasourceConfig,
        tech_meta: dict[str, Any],
        columns: dict[str, Any],
    ) -> geminidataanalytics.BigQueryTableReference:
        """Build a BigQueryTableReference with schema fields."""
        bq_ref = geminidataanalytics.BigQueryTableReference()
        bq_ref.project_id = ds.project_id
        bq_ref.dataset_id = ds.dataset_id
        bq_ref.table_id = ds.table_id

        # Schema
        schema = geminidataanalytics.Schema()
        schema.description = tech_meta.get("description", "")
        schema.fields = [
            geminidataanalytics.Field(
                name=col_name,
                description=col_meta.get("description", ""),
            )
            for col_name, col_meta in columns.items()
        ]
        bq_ref.schema = schema

        return bq_ref
