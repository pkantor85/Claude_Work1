"""Load agent configurations and metadata from GCS or local files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from google.cloud import storage

from config.schema import AgentsConfig

logger = logging.getLogger(__name__)


def load_config_from_gcs(bucket_name: str, object_path: str, project_id: str | None = None) -> AgentsConfig:
    """Load and validate agent config JSON from a GCS bucket.

    Args:
        bucket_name: GCS bucket name.
        object_path: Path to the config JSON object inside the bucket.
        project_id: Optional GCP project for the storage client.

    Returns:
        Validated AgentsConfig.
    """
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_path)
    raw = blob.download_as_text()
    data = json.loads(raw)
    logger.info("Loaded config from gs://%s/%s", bucket_name, object_path)
    return AgentsConfig(**data)


def load_config_from_file(path: str | Path) -> AgentsConfig:
    """Load and validate agent config JSON from a local file.

    Args:
        path: Local filesystem path to config JSON.

    Returns:
        Validated AgentsConfig.
    """
    with open(path) as f:
        data = json.load(f)
    logger.info("Loaded config from %s", path)
    return AgentsConfig(**data)


def load_metadata_from_gcs(
    bucket_name: str, object_path: str, project_id: str | None = None
) -> dict[str, Any]:
    """Load a metadata JSON file from GCS.

    Args:
        bucket_name: GCS bucket name.
        object_path: Path to the metadata JSON inside the bucket.
        project_id: Optional GCP project for the storage client.

    Returns:
        Parsed metadata dictionary.
    """
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_path)
    raw = blob.download_as_text()
    metadata = json.loads(raw)
    logger.info("Loaded metadata from gs://%s/%s", bucket_name, object_path)
    return metadata


def load_metadata_from_file(path: str | Path) -> dict[str, Any]:
    """Load a metadata JSON file from the local filesystem.

    Args:
        path: Local path to metadata JSON.

    Returns:
        Parsed metadata dictionary.
    """
    with open(path) as f:
        return json.load(f)
