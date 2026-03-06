# ============================================================
# setup_gcp.ps1 — Enable required APIs and set IAM roles
# ============================================================
#
# Usage:
#   $env:PROJECT_ID = "your-gcp-project-id"
#   $env:SERVICE_ACCOUNT = "your-sa@your-project.iam.gserviceaccount.com"  # optional
#   .\scripts\setup_gcp.ps1
#
# ============================================================

$ErrorActionPreference = "Stop"

# ── Configuration ─────────────────────────────────────────

if (-not $env:PROJECT_ID) {
    Write-Error "ERROR: Set PROJECT_ID environment variable first. Example: `$env:PROJECT_ID = 'your-project-id'"
    exit 1
}

$PROJECT_ID = $env:PROJECT_ID
$REGION = if ($env:REGION) { $env:REGION } else { "us-central1" }
$SERVICE_ACCOUNT = $env:SERVICE_ACCOUNT

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  BigQuery Data Analytics Agent — GCP Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Project:  $PROJECT_ID"
Write-Host "  Region:   $REGION"
Write-Host "  SA:       $(if ($SERVICE_ACCOUNT) { $SERVICE_ACCOUNT } else { '(using user credentials)' })"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Enable Required APIs ──────────────────────────────

Write-Host "▶ Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable `
    geminidataanalytics.googleapis.com `
    bigquery.googleapis.com `
    cloudaicompanion.googleapis.com `
    dataplex.googleapis.com `
    storage.googleapis.com `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    --project="$PROJECT_ID"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to enable APIs. Check your project ID and permissions."
    exit 1
}
Write-Host "✅ APIs enabled." -ForegroundColor Green
Write-Host ""

# ── 2. Set up Application Default Credentials ────────────

Write-Host "▶ Setting up Application Default Credentials..." -ForegroundColor Yellow
gcloud auth application-default login 2>$null
gcloud auth application-default set-quota-project "$PROJECT_ID" 2>$null
Write-Host "✅ ADC configured." -ForegroundColor Green
Write-Host ""

# ── 3. Grant IAM Roles (if service account specified) ─────

if ($SERVICE_ACCOUNT) {
    Write-Host "▶ Granting IAM roles to $SERVICE_ACCOUNT..." -ForegroundColor Yellow

    $roles = @(
        "roles/geminidataanalytics.admin",
        "roles/bigquery.dataViewer",
        "roles/bigquery.user",
        "roles/storage.objectViewer",
        "roles/dataplex.viewer",
        "roles/run.developer"
    )

    foreach ($role in $roles) {
        Write-Host "  Adding $role..."
        gcloud projects add-iam-policy-binding "$PROJECT_ID" `
            --member="serviceAccount:$SERVICE_ACCOUNT" `
            --role="$role" `
            --condition=None `
            --quiet 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ⚠️  Could not add $role (may already exist)" -ForegroundColor DarkYellow
        }
    }
    Write-Host "✅ IAM roles granted." -ForegroundColor Green
}
else {
    Write-Host "ℹ️  No SERVICE_ACCOUNT specified — skipping IAM role grants." -ForegroundColor Cyan
    Write-Host "   Make sure your user account has the required roles:"
    Write-Host "   • roles/geminidataanalytics.admin"
    Write-Host "   • roles/bigquery.dataViewer + roles/bigquery.user"
    Write-Host "   • roles/storage.objectViewer"
    Write-Host "   • roles/dataplex.viewer (optional)"
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  ✅  GCP setup complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. pip install -r requirements.txt"
Write-Host "  2. cp .streamlit/secrets.toml.template .streamlit/secrets.toml"
Write-Host "  3. Edit .streamlit/secrets.toml with your project details"
Write-Host "  4. python -m scripts.provision_agents --config-local config/agents_config.yaml"
Write-Host "  5. streamlit run ui/app.py"
