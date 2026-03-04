"""Pydantic models for agent configuration validation."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class DatasourceConfig(BaseModel):
    """BigQuery table reference configuration."""

    project_id: str
    dataset_id: str
    table_id: str


class DataplexGlossaryConfig(BaseModel):
    """Dataplex glossary reference."""

    project_id: str
    location: str = "us"
    glossary_id: str


class PromptSettings(BaseModel):
    """Settings passed to the LLM prompt generator."""

    agent_name: str = "SQL Assistant"
    domain: str = "Data Analytics"


class AgentConfig(BaseModel):
    """Configuration for a single CA API data agent."""

    agent_id: str
    display_name: str
    description: str = ""
    metadata_file: str = Field(
        ..., description="GCS object path to the metadata JSON file"
    )
    datasources: list[DatasourceConfig]
    dataplex_glossary: Optional[DataplexGlossaryConfig] = None
    prompt_settings: PromptSettings = PromptSettings()
    labels: dict[str, str] = {}
    max_bytes_billed: int = 0


class AgentsConfig(BaseModel):
    """Top-level configuration containing all agents to provision."""

    project_id: str
    location: str = "global"
    gcs_bucket: str
    agents: list[AgentConfig]
