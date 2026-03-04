#!/usr/bin/env bash
# Enable required GCP APIs and install Python dependencies.
#
# Usage:
#   ./setup_gcp.sh <PROJECT_ID>

set -euo pipefail

PROJECT_ID="${1:?Usage: setup_gcp.sh <PROJECT_ID>}"

echo "==> Enabling APIs for project: ${PROJECT_ID}"
gcloud services enable \
  geminidataanalytics.googleapis.com \
  bigquery.googleapis.com \
  cloudaicompanion.googleapis.com \
  dataplex.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT_ID}"

echo "==> Installing Python dependencies"
pip install -r "$(dirname "$0")/../requirements.txt"

echo "==> Done. APIs enabled and dependencies installed."
