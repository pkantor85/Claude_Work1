"""
metadata_loader — Load BigQuery / Dataplex metadata from GCS JSON files.

The metadata JSON file (e.g.
``4_business_glossary_and_KPI_Dataplex_vs_BigQuery.json``) contains:

* ``config``                      — dataset / table identifiers
* ``bigquery_technical_metadata`` — column names, types, descriptions
* ``dataplex_business_glossary``  — business term → column mappings
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from google.cloud import storage

from src.utils import get_logger

logger = get_logger(__name__)


# ── Dataclasses ───────────────────────────────────────────


@dataclass
class ColumnMeta:
    """Metadata for a single BigQuery column."""

    name: str
    description: str = ""
    data_type_hint: str = "Unknown"
    example_values: list[str] = field(default_factory=list)
    calculation_logic: str = ""


@dataclass
class BusinessTerm:
    """A Dataplex business glossary entry."""

    business_term: str
    definition: str = ""
    data_steward: str = ""
    update_frequency: str = ""
    security_classification: str = ""
    business_function: str = ""
    linked_assets: list[str] = field(default_factory=list)


@dataclass
class MetadataBundle:
    """
    Combined BigQuery technical metadata and Dataplex business glossary
    for a single table / dataset.
    """

    dataset: str
    table: str
    table_description: str
    columns: list[ColumnMeta]
    business_terms: list[BusinessTerm]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


# ── Parsing ───────────────────────────────────────────────


def parse_metadata(raw: dict[str, Any]) -> MetadataBundle:
    """
    Parse a metadata dictionary (as stored in GCS) into a typed
    :class:`MetadataBundle`.
    """
    config = raw.get("config", {})
    tech = raw.get("bigquery_technical_metadata", {})
    glossary = raw.get("dataplex_business_glossary", {})

    columns: list[ColumnMeta] = []
    for col_name, col_meta in tech.get("columns", {}).items():
        columns.append(
            ColumnMeta(
                name=col_name,
                description=col_meta.get("description", ""),
                data_type_hint=col_meta.get("data_type_hint", "Unknown"),
                example_values=col_meta.get("example_values", []),
                calculation_logic=col_meta.get("calculation_logic", ""),
            )
        )

    terms: list[BusinessTerm] = []
    for term_data in glossary.get("terms", []):
        terms.append(
            BusinessTerm(
                business_term=term_data.get("business_term", ""),
                definition=term_data.get("definition", ""),
                data_steward=term_data.get("data_steward", ""),
                update_frequency=term_data.get("update_frequency", ""),
                security_classification=term_data.get(
                    "security_classification", ""
                ),
                business_function=term_data.get("business_function", ""),
                linked_assets=term_data.get("linked_assets", []),
            )
        )

    return MetadataBundle(
        dataset=config.get("dataset", "unknown_dataset"),
        table=config.get("table", "unknown_table"),
        table_description=tech.get("description", ""),
        columns=columns,
        business_terms=terms,
        raw=raw,
    )


# ── GCS / File Loaders ───────────────────────────────────


def load_metadata_from_gcs(
    bucket_name: str,
    blob_path: str,
    project_id: Optional[str] = None,
) -> MetadataBundle:
    """Download a metadata JSON file from GCS and parse it."""
    logger.info(
        "Loading metadata from gs://%s/%s", bucket_name, blob_path
    )
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    raw: dict[str, Any] = json.loads(blob.download_as_text())
    return parse_metadata(raw)


def load_metadata_from_file(path: str | Path) -> MetadataBundle:
    """Load a metadata JSON file from the local filesystem."""
    path = Path(path)
    logger.info("Loading metadata from %s", path)
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return parse_metadata(raw)


def load_prompt_text_from_gcs(
    bucket_name: str,
    blob_path: str,
    project_id: Optional[str] = None,
) -> str:
    """Download a pre-built system instruction text file from GCS."""
    logger.info(
        "Loading prompt text from gs://%s/%s", bucket_name, blob_path
    )
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    return blob.download_as_text()
