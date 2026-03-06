"""
agent_manager — CRUD operations for Conversational Analytics API DataAgents.

Wraps the ``google.cloud.geminidataanalytics`` Python SDK to:
* Create agents from configuration + metadata
* Get / list / update / delete agents
* Set IAM policies for sharing
"""

from __future__ import annotations

from typing import Optional

from google.cloud import geminidataanalytics
from google.iam.v1 import iam_policy_pb2, policy_pb2
from google.protobuf import field_mask_pb2

from src.config_loader import AgentConfig, AgentsConfig, GlobalConfig
from src.metadata_loader import (
    MetadataBundle,
    load_metadata_from_gcs,
    load_prompt_text_from_gcs,
)
from src.prompt_generator import generate_system_instruction
from src.utils import agent_resource_name, get_logger, parent_resource_name

logger = get_logger(__name__)


# ── Client singletons ─────────────────────────────────────

_agent_client: Optional[geminidataanalytics.DataAgentServiceClient] = None


def _get_agent_client() -> geminidataanalytics.DataAgentServiceClient:
    global _agent_client
    if _agent_client is None:
        _agent_client = geminidataanalytics.DataAgentServiceClient()
    return _agent_client


# ── Helpers ────────────────────────────────────────────────


def _build_bq_table_reference(
    ds_cfg, metadata: Optional[MetadataBundle]
) -> geminidataanalytics.BigQueryTableReference:
    """
    Build a ``BigQueryTableReference`` from a datasource config entry,
    enriching it with column-level schema descriptions from *metadata*
    when available.
    """
    ref = geminidataanalytics.BigQueryTableReference()
    ref.project_id = ds_cfg.project_id
    ref.dataset_id = ds_cfg.dataset_id
    ref.table_id = ds_cfg.table_id

    if metadata:
        ref.schema = geminidataanalytics.Schema()
        ref.schema.description = metadata.table_description
        ref.schema.fields = [
            geminidataanalytics.Field(
                name=col.name,
                description=col.description,
            )
            for col in metadata.columns
        ]
    return ref


def _resolve_system_instruction(
    agent_cfg: AgentConfig,
    global_cfg: GlobalConfig,
    metadata: Optional[MetadataBundle] = None,
) -> str:
    """
    Resolve the system instruction for an agent.

    Priority:
    1. Pre-built prompt text file in GCS  (``prompt_gcs_path``)
    2. Auto-generated from metadata JSON   (``metadata_gcs_path``)

    If *metadata* is already loaded it will be reused instead of
    fetching from GCS again.
    """
    pc = agent_cfg.prompt_config
    bucket = global_cfg.gcs_bucket

    if pc.prompt_gcs_path:
        logger.info(
            "Using pre-built prompt from gs://%s/%s",
            bucket,
            pc.prompt_gcs_path,
        )
        return load_prompt_text_from_gcs(
            bucket_name=bucket,
            blob_path=pc.prompt_gcs_path,
            project_id=global_cfg.project_id,
        )

    # Auto-generate from metadata
    if metadata is None:
        if not pc.metadata_gcs_path:
            raise ValueError(
                f"Agent '{agent_cfg.agent_id}': metadata_gcs_path is "
                "required when prompt_gcs_path is not set"
            )
        metadata = load_metadata_from_gcs(
            bucket_name=bucket,
            blob_path=pc.metadata_gcs_path,
            project_id=global_cfg.project_id,
        )
    return generate_system_instruction(
        metadata=metadata,
        agent_name=pc.agent_name,
        domain=pc.domain,
    )


def _resolve_metadata(
    agent_cfg: AgentConfig,
    global_cfg: GlobalConfig,
) -> Optional[MetadataBundle]:
    """Load metadata if a metadata_gcs_path is configured."""
    pc = agent_cfg.prompt_config
    if pc.metadata_gcs_path:
        return load_metadata_from_gcs(
            bucket_name=global_cfg.gcs_bucket,
            blob_path=pc.metadata_gcs_path,
            project_id=global_cfg.project_id,
        )
    return None


# ── CRUD Operations ───────────────────────────────────────


def create_agent(
    agent_cfg: AgentConfig,
    global_cfg: GlobalConfig,
) -> geminidataanalytics.DataAgent:
    """
    Create a single CA API Data Agent from configuration.

    Steps:
    1. Resolve system instruction (generate or load from GCS).
    2. Build BigQuery table references with schema descriptions.
    3. Configure datasource references.
    4. Build published context (instruction + datasources + options).
    5. Call ``create_data_agent_sync``.
    6. Optionally set IAM policy.
    """
    client = _get_agent_client()
    project_id = global_cfg.project_id
    location = global_cfg.location

    logger.info(
        "Creating agent '%s' in %s/%s",
        agent_cfg.agent_id,
        project_id,
        location,
    )

    # 1. Metadata (loaded once, used for both instruction and schema)
    metadata = _resolve_metadata(agent_cfg, global_cfg)

    # 2. System instruction (reuses metadata to avoid duplicate GCS fetch)
    system_instruction = _resolve_system_instruction(
        agent_cfg, global_cfg, metadata=metadata
    )

    # 3. BigQuery table references
    table_refs = [
        _build_bq_table_reference(ds, metadata)
        for ds in agent_cfg.datasources
    ]

    # 4. Datasource references
    datasource_refs = geminidataanalytics.DatasourceReferences()
    datasource_refs.bq.table_references = table_refs

    # 5. Published context
    published_context = geminidataanalytics.Context()
    published_context.system_instruction = system_instruction
    published_context.datasource_references = datasource_refs

    if agent_cfg.options.python_analysis_enabled:
        published_context.options.analysis.python.enabled = True

    # 6. Agent object
    data_agent = geminidataanalytics.DataAgent()
    data_agent.data_analytics_agent.published_context = published_context
    data_agent.description = agent_cfg.description

    request = geminidataanalytics.CreateDataAgentRequest(
        parent=parent_resource_name(project_id, location),
        data_agent_id=agent_cfg.agent_id,
        data_agent=data_agent,
    )

    try:
        response = client.create_data_agent_sync(request=request)
        logger.info("✅ Agent created: %s", response.name)
    except Exception as exc:
        logger.error("❌ Failed to create agent '%s': %s", agent_cfg.agent_id, exc)
        raise

    # 7. IAM bindings
    if agent_cfg.iam_bindings:
        _set_iam_policy(agent_cfg, global_cfg)

    return response


def get_agent(
    agent_id: str,
    project_id: str,
    location: str = "global",
) -> geminidataanalytics.DataAgent:
    """Retrieve an existing Data Agent."""
    client = _get_agent_client()
    request = geminidataanalytics.GetDataAgentRequest(
        name=agent_resource_name(project_id, location, agent_id),
    )
    return client.get_data_agent(request=request)


def list_agents(
    project_id: str,
    location: str = "global",
) -> list[geminidataanalytics.DataAgent]:
    """List all Data Agents in the project."""
    client = _get_agent_client()
    request = geminidataanalytics.ListDataAgentsRequest(
        parent=parent_resource_name(project_id, location),
    )
    return list(client.list_data_agents(request=request))


def update_agent(
    agent_cfg: AgentConfig,
    global_cfg: GlobalConfig,
    update_fields: Optional[list[str]] = None,
) -> geminidataanalytics.DataAgent:
    """
    Update an existing Data Agent.

    By default updates the description and published context (system
    instruction + datasources).
    """
    client = _get_agent_client()
    project_id = global_cfg.project_id
    location = global_cfg.location

    metadata = _resolve_metadata(agent_cfg, global_cfg)
    system_instruction = _resolve_system_instruction(
        agent_cfg, global_cfg, metadata=metadata
    )

    table_refs = [
        _build_bq_table_reference(ds, metadata)
        for ds in agent_cfg.datasources
    ]
    datasource_refs = geminidataanalytics.DatasourceReferences()
    datasource_refs.bq.table_references = table_refs

    published_context = geminidataanalytics.Context()
    published_context.system_instruction = system_instruction
    published_context.datasource_references = datasource_refs
    if agent_cfg.options.python_analysis_enabled:
        published_context.options.analysis.python.enabled = True

    data_agent = geminidataanalytics.DataAgent()
    data_agent.data_analytics_agent.published_context = published_context
    data_agent.name = agent_resource_name(
        project_id, location, agent_cfg.agent_id
    )
    data_agent.description = agent_cfg.description

    if update_fields is None:
        update_fields = [
            "description",
            "data_analytics_agent.published_context",
        ]

    update_mask = field_mask_pb2.FieldMask(paths=update_fields)

    request = geminidataanalytics.UpdateDataAgentRequest(
        data_agent=data_agent,
        update_mask=update_mask,
    )

    try:
        response = client.update_data_agent_sync(request=request)
        logger.info("✅ Agent updated: %s", response.name)
        return response
    except Exception as exc:
        logger.error(
            "❌ Failed to update agent '%s': %s", agent_cfg.agent_id, exc
        )
        raise


def delete_agent(
    agent_id: str,
    project_id: str,
    location: str = "global",
) -> None:
    """Soft-delete a Data Agent (recoverable within 30 days)."""
    client = _get_agent_client()
    request = geminidataanalytics.DeleteDataAgentRequest(
        name=agent_resource_name(project_id, location, agent_id),
    )
    try:
        client.delete_data_agent_sync(request=request)
        logger.info("🗑️  Agent deleted: %s", agent_id)
    except Exception as exc:
        logger.error("❌ Failed to delete agent '%s': %s", agent_id, exc)
        raise


# ── IAM ───────────────────────────────────────────────────


def _set_iam_policy(
    agent_cfg: AgentConfig,
    global_cfg: GlobalConfig,
) -> None:
    """Apply IAM bindings from config to the agent."""
    client = _get_agent_client()
    resource = agent_resource_name(
        global_cfg.project_id, global_cfg.location, agent_cfg.agent_id
    )

    bindings = []
    for binding_cfg in agent_cfg.iam_bindings:
        members = [
            m if ":" in m else f"user:{m}"
            for m in binding_cfg.members
        ]
        bindings.append(
            policy_pb2.Binding(
                role=binding_cfg.role,
                members=members,
            )
        )

    policy = policy_pb2.Policy(bindings=bindings)
    request = iam_policy_pb2.SetIamPolicyRequest(
        resource=resource, policy=policy
    )

    try:
        client.set_iam_policy(request=request)
        logger.info(
            "🔐 IAM policy set for agent '%s'", agent_cfg.agent_id
        )
    except Exception as exc:
        logger.warning(
            "⚠️  Could not set IAM policy for '%s': %s",
            agent_cfg.agent_id,
            exc,
        )


# ── Bulk Provisioning ─────────────────────────────────────


def provision_all_agents(config: AgentsConfig) -> list[str]:
    """
    Provision (create or update) every agent defined in the configuration.

    Returns list of created/updated agent resource names.
    """
    global_cfg = config.global_config
    results: list[str] = []

    existing = {
        a.name.split("/")[-1]: a
        for a in list_agents(global_cfg.project_id, global_cfg.location)
    }

    for agent_cfg in config.agents:
        try:
            if agent_cfg.agent_id in existing:
                logger.info(
                    "Agent '%s' exists — updating …", agent_cfg.agent_id
                )
                resp = update_agent(agent_cfg, global_cfg)
            else:
                resp = create_agent(agent_cfg, global_cfg)
            results.append(resp.name)
        except Exception as exc:
            logger.error(
                "Skipping agent '%s' due to error: %s",
                agent_cfg.agent_id,
                exc,
            )

    logger.info(
        "Provisioning complete: %d/%d agents OK",
        len(results),
        len(config.agents),
    )
    return results
