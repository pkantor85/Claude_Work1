"""
provision_agents — CLI tool to bulk-create or update all agents from config.

Usage:
    python -m scripts.provision_agents \
        --config-gcs-uri gs://BUCKET/config/agents_config.yaml

    python -m scripts.provision_agents \
        --config-local config/agents_config.yaml
"""

from __future__ import annotations

import argparse
import sys
from urllib.parse import urlparse

from src.agent_manager import provision_all_agents
from src.config_loader import load_config_from_file, load_config_from_gcs
from src.utils import get_logger

logger = get_logger("provision_agents")


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    """Parse ``gs://bucket/path`` into (bucket, path)."""
    parsed = urlparse(uri)
    if parsed.scheme != "gs":
        raise ValueError(f"Expected gs:// URI, got: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision BQ Data Agents from configuration."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--config-gcs-uri",
        help="GCS URI to agents_config.yaml  (gs://bucket/path)",
    )
    group.add_argument(
        "--config-local",
        help="Local path to agents_config.yaml",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate config without creating agents.",
    )

    args = parser.parse_args()

    # Load config
    if args.config_gcs_uri:
        bucket, path = _parse_gcs_uri(args.config_gcs_uri)
        config = load_config_from_gcs(bucket, path)
    else:
        config = load_config_from_file(args.config_local)

    logger.info(
        "Loaded config: project=%s, %d agent(s) defined",
        config.global_config.project_id,
        len(config.agents),
    )

    for agent in config.agents:
        logger.info(
            "  • %s — %s (%d datasource(s))",
            agent.agent_id,
            agent.display_name,
            len(agent.datasources),
        )

    if args.dry_run:
        logger.info("Dry-run mode — no agents created.")
        return

    # Provision
    results = provision_all_agents(config)
    logger.info("Done. %d agent(s) provisioned.", len(results))
    for name in results:
        logger.info("  ✅ %s", name)


if __name__ == "__main__":
    main()
