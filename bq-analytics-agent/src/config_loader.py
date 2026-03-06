"""
config_loader — Load agent configuration from GCS or local YAML files.

The master configuration (`agents_config.yaml`) defines every agent that the
system should provision.  This module downloads the file from Cloud Storage,
validates it against Pydantic models, and returns typed dataclasses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from google.cloud import storage
from pydantic import BaseModel, Field, model_validator

from src.utils import get_logger

logger = get_logger(__name__)


# ── Pydantic Models ───────────────────────────────────────


class DatasourceConfig(BaseModel):
    """A single BigQuery table reference."""

    type: str = "bigquery"
    project_id: str
    dataset_id: str
    table_id: str


class PromptConfig(BaseModel):
    """Controls how the system instruction is generated / loaded."""

    agent_name: str
    domain: str
    metadata_gcs_path: Optional[str] = None
    prompt_gcs_path: Optional[str] = None

    @model_validator(mode="after")
    def check_at_least_one_source(self) -> "PromptConfig":
        if not self.metadata_gcs_path and not self.prompt_gcs_path:
            raise ValueError(
                "prompt_config must specify either 'metadata_gcs_path' "
                "or 'prompt_gcs_path'"
            )
        return self


class DataplexConfig(BaseModel):
    """Optional Dataplex glossary reference."""

    glossary_id: str
    glossary_location: str = "us"


class AgentOptions(BaseModel):
    """Runtime options for the agent."""

    python_analysis_enabled: bool = False
    stateful_chat: bool = True


class IamBinding(BaseModel):
    """IAM role → members mapping for agent sharing."""

    role: str
    members: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Full definition for a single Data Agent."""

    agent_id: str
    display_name: str
    description: str = ""
    prompt_config: PromptConfig
    datasources: list[DatasourceConfig]
    dataplex: Optional[DataplexConfig] = None
    options: AgentOptions = Field(default_factory=AgentOptions)
    iam_bindings: list[IamBinding] = Field(default_factory=list)


class GlobalConfig(BaseModel):
    """Project-wide settings."""

    project_id: str
    location: str = "global"
    gcs_bucket: str
    metadata_base_path: str = ""


class AgentsConfig(BaseModel):
    """Root configuration model."""

    global_config: GlobalConfig = Field(..., alias="global")
    agents: list[AgentConfig]

    model_config = {"populate_by_name": True}


# ── Loaders ───────────────────────────────────────────────


def load_config_from_gcs(
    bucket_name: str,
    blob_path: str,
    project_id: Optional[str] = None,
) -> AgentsConfig:
    """
    Download ``agents_config.yaml`` from GCS and return a validated
    :class:`AgentsConfig`.
    """
    logger.info("Loading config from gs://%s/%s", bucket_name, blob_path)
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    yaml_text = blob.download_as_text()
    return _parse_yaml(yaml_text)


def load_config_from_file(path: str | Path) -> AgentsConfig:
    """
    Load ``agents_config.yaml`` from a local file path and return a
    validated :class:`AgentsConfig`.
    """
    path = Path(path)
    logger.info("Loading config from %s", path)
    yaml_text = path.read_text(encoding="utf-8")
    return _parse_yaml(yaml_text)


def _parse_yaml(yaml_text: str) -> AgentsConfig:
    """Parse raw YAML text into a validated config object."""
    data: dict[str, Any] = yaml.safe_load(yaml_text)
    return AgentsConfig.model_validate(data)
