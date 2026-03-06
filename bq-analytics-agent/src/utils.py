"""
Shared utilities: authentication, logging, and helper functions.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

import google.auth
from google.auth import credentials as ga_credentials


# ── Logging ────────────────────────────────────────────────

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create a consistently-formatted logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ── Authentication ─────────────────────────────────────────

def get_default_credentials(
    quota_project: Optional[str] = None,
) -> tuple[ga_credentials.Credentials, str]:
    """
    Return Application Default Credentials and the associated project ID.

    If *quota_project* is supplied it is set on the credentials so that
    billing is attributed correctly.
    """
    credentials, project = google.auth.default()
    if quota_project:
        credentials = credentials.with_quota_project(quota_project)
    return credentials, project or ""


# ── Resource-name helpers ──────────────────────────────────

def agent_resource_name(project_id: str, location: str, agent_id: str) -> str:
    """Build the fully-qualified resource name for a CA API DataAgent."""
    return f"projects/{project_id}/locations/{location}/dataAgents/{agent_id}"


def conversation_resource_name(
    project_id: str, location: str, conversation_id: str
) -> str:
    """Build the fully-qualified resource name for a conversation."""
    return (
        f"projects/{project_id}/locations/{location}"
        f"/conversations/{conversation_id}"
    )


def parent_resource_name(project_id: str, location: str) -> str:
    """Build the parent resource path for list/create operations."""
    return f"projects/{project_id}/locations/{location}"
