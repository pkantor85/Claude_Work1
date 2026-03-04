#!/usr/bin/env python3
"""CLI script to provision all BigQuery CA API agents from a config file.

Usage:
    # From GCS:
    python provision_agents.py --gcs-bucket my-bucket --gcs-path agents_config.json --project my-project

    # From local file:
    python provision_agents.py --local ../sample_configs/agents_config.json

    # Dry run (preview only):
    python provision_agents.py --local ../sample_configs/agents_config.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.provisioner import AgentProvisioner
from config.loader import (
    load_config_from_file,
    load_config_from_gcs,
    load_metadata_from_file,
    load_metadata_from_gcs,
)
from prompts.generator import generate_llm_system_prompt

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision BigQuery CA API data agents.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--local", type=str, help="Path to local agents_config.json.")
    source.add_argument("--gcs-bucket", type=str, help="GCS bucket containing config.")
    parser.add_argument("--gcs-path", type=str, default="agents_config.json", help="Config object path in bucket.")
    parser.add_argument("--project", type=str, help="GCP project ID (overrides config value).")
    parser.add_argument("--dry-run", action="store_true", help="Preview agents without creating them.")
    parser.add_argument("--local-metadata-dir", type=str, help="Dir with local metadata JSONs (for offline testing).")
    args = parser.parse_args()

    # Load config
    if args.local:
        config = load_config_from_file(args.local)
    else:
        project = args.project or None
        config = load_config_from_gcs(args.gcs_bucket, args.gcs_path, project)

    project_id = args.project or config.project_id

    # Load metadata for each agent
    metadata_map: dict[str, dict] = {}
    for agent_cfg in config.agents:
        if args.local_metadata_dir:
            meta_path = Path(args.local_metadata_dir) / agent_cfg.metadata_file
            metadata_map[agent_cfg.agent_id] = load_metadata_from_file(meta_path)
        else:
            metadata_map[agent_cfg.agent_id] = load_metadata_from_gcs(
                config.gcs_bucket, agent_cfg.metadata_file, project_id
            )

    if args.dry_run:
        logger.info("=== DRY RUN — no agents will be created ===")
        for agent_cfg in config.agents:
            meta = metadata_map[agent_cfg.agent_id]
            prompt = generate_llm_system_prompt(
                meta,
                agent_name=agent_cfg.prompt_settings.agent_name,
                domain=agent_cfg.prompt_settings.domain,
            )
            print(f"\n--- Agent: {agent_cfg.display_name} (ID: {agent_cfg.agent_id}) ---")
            print(f"  Datasources: {[f'{d.project_id}.{d.dataset_id}.{d.table_id}' for d in agent_cfg.datasources]}")
            print(f"  System prompt ({len(prompt)} chars):")
            print(f"  {prompt[:200]}...")
        return

    # Provision
    provisioner = AgentProvisioner(project_id=project_id, location=config.location)
    results = provisioner.provision_all(config, metadata_map)

    print(f"\n=== Provisioned {len(results)} agent(s) ===")
    for agent in results:
        print(f"  {agent.name}")


if __name__ == "__main__":
    main()
