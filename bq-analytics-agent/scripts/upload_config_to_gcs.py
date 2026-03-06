"""
upload_config_to_gcs — Upload local configuration files to GCS.

Usage:
    python -m scripts.upload_config_to_gcs \
        --local-path config/agents_config.yaml \
        --gcs-uri gs://BUCKET/config/agents_config.yaml
"""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse

from google.cloud import storage

from src.utils import get_logger

logger = get_logger("upload_config")


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "gs":
        raise ValueError(f"Expected gs:// URI, got: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upload local config / metadata files to GCS."
    )
    parser.add_argument(
        "--local-path",
        required=True,
        help="Path to the local file to upload.",
    )
    parser.add_argument(
        "--gcs-uri",
        required=True,
        help="Destination GCS URI (gs://bucket/path).",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="GCP project ID (optional, uses default).",
    )

    args = parser.parse_args()

    local_path = Path(args.local_path)
    if not local_path.exists():
        logger.error("File not found: %s", local_path)
        sys.exit(1)

    bucket_name, blob_path = _parse_gcs_uri(args.gcs_uri)

    client = storage.Client(project=args.project)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)

    logger.info(
        "Uploading %s → gs://%s/%s", local_path, bucket_name, blob_path
    )
    blob.upload_from_filename(str(local_path))
    logger.info("✅ Upload complete.")


if __name__ == "__main__":
    main()
