#!/usr/bin/env bash
# ============================================================
# setup_gcp.sh — Enable required APIs and set IAM roles
# ============================================================
#
# Usage:
#   export PROJECT_ID="your-gcp-project-id"
#   export SERVICE_ACCOUNT="your-sa@your-project.iam.gserviceaccount.com"
#   bash scripts/setup_gcp.sh
#
# ============================================================

set -euo pipefail

# ── Configuration ─────────────────────────────────────────

PROJECT_ID="${PROJECT_ID:?ERROR: Set PROJECT_ID environment variable}"
REGION="${REGION:-us-central1}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-}"

echo "============================================================"
echo "  BigQuery Data Analytics Agent — GCP Setup"
echo "============================================================"
echo "  Project:  ${PROJECT_ID}"
echo "  Region:   ${REGION}"
echo "  SA:       ${SERVICE_ACCOUNT:-'(using user credentials)'}"
echo "============================================================"
echo ""

# ── 1. Enable Required APIs ──────────────────────────────

echo "▶ Enabling required APIs..."
gcloud services enable \
    geminidataanalytics.googleapis.com \
    bigquery.googleapis.com \
    cloudaicompanion.googleapis.com \
    dataplex.googleapis.com \
    storage.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    --project="${PROJECT_ID}"
echo "✅ APIs enabled."
echo ""

# ── 2. Set up Application Default Credentials ────────────

echo "▶ Setting up Application Default Credentials..."
gcloud auth application-default login 2>/dev/null || true
gcloud auth application-default set-quota-project "${PROJECT_ID}" 2>/dev/null || true
echo "✅ ADC configured."
echo ""

# ── 3. Grant IAM Roles (if service account specified) ─────

if [[ -n "${SERVICE_ACCOUNT}" ]]; then
    echo "▶ Granting IAM roles to ${SERVICE_ACCOUNT}..."

    declare -a ROLES=(
        "roles/geminidataanalytics.admin"
        "roles/bigquery.dataViewer"
        "roles/bigquery.user"
        "roles/storage.objectViewer"
        "roles/dataplex.viewer"
        "roles/run.developer"
    )

    for ROLE in "${ROLES[@]}"; do
        echo "  Adding ${ROLE}..."
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${SERVICE_ACCOUNT}" \
            --role="${ROLE}" \
            --condition=None \
            --quiet 2>/dev/null || echo "  ⚠️  Could not add ${ROLE} (may already exist)"
    done
    echo "✅ IAM roles granted."
else
    echo "ℹ️  No SERVICE_ACCOUNT specified — skipping IAM role grants."
    echo "   Make sure your user account has the required roles:"
    echo "   • roles/geminidataanalytics.admin"
    echo "   • roles/bigquery.dataViewer + roles/bigquery.user"
    echo "   • roles/storage.objectViewer"
    echo "   • roles/dataplex.viewer (optional)"
fi

echo ""
echo "============================================================"
echo "  ✅  GCP setup complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "  1. pip install -r requirements.txt"
echo "  2. cp .streamlit/secrets.toml.template .streamlit/secrets.toml"
echo "  3. Edit .streamlit/secrets.toml with your project details"
echo "  4. python -m scripts.provision_agents --config-local config/agents_config.yaml"
echo "  5. streamlit run ui/app.py"
