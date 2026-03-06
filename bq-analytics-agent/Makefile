.PHONY: install dev-install test lint run provision upload-config setup-gcp deploy clean

# ──────────────────────────────────────────────
# Installation
# ──────────────────────────────────────────────
install:
	pip install -r requirements.txt

dev-install:
	pip install -e ".[dev]"

# ──────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────
test:
	pytest tests/ -v

lint:
	python -m ruff check src/ ui/ scripts/ tests/

# ──────────────────────────────────────────────
# Run Streamlit UI locally
# ──────────────────────────────────────────────
run:
	streamlit run ui/app.py --server.port 8501

# ──────────────────────────────────────────────
# Agent Provisioning
# ──────────────────────────────────────────────
provision:
	python -m scripts.provision_agents --config-gcs-uri gs://$(BUCKET)/config/agents_config.yaml

upload-config:
	python -m scripts.upload_config_to_gcs --local-path config/agents_config.yaml --gcs-uri gs://$(BUCKET)/config/agents_config.yaml

# ──────────────────────────────────────────────
# GCP Setup
# ──────────────────────────────────────────────
setup-gcp:
	bash scripts/setup_gcp.sh

# ──────────────────────────────────────────────
# Docker / Cloud Run Deployment
# ──────────────────────────────────────────────
deploy:
	gcloud builds submit --config deploy/cloudbuild.yaml .

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache build dist *.egg-info
