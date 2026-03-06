# BigQuery Data Analytics Agent System

A production-grade system for programmatically creating and managing **domain-specific BigQuery Data Agents** using Google Cloud's **Conversational Analytics (CA) API**. Agents are dynamically provisioned from YAML configuration stored in GCS, with system instructions auto-generated from Dataplex/BigQuery metadata.

## Architecture

```
┌─────────────────┐    ┌────────────────────────┐    ┌────────────────┐
│  Cloud Storage   │    │  Conversational        │    │   BigQuery     │
│  (GCS Bucket)    │    │  Analytics API         │    │   Datasets     │
│                  │    │                        │    │                │
│ • agents_config  │───▶│  • DataAgentService    │───▶│ • gold_business│
│   .yaml          │    │  • DataChatService     │    │   .gold_kpi_*  │
│ • metadata/*.json│    │                        │    │                │
└─────────────────┘    └────────────┬───────────┘    └────────────────┘
                                    │
                       ┌────────────▼───────────┐
                       │  Cloud Run (Streamlit)  │
                       │  • Agent Management     │
                       │  • Chat Interface       │
                       │  • Conversation History │
                       └─────────────────────────┘
```

## Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud` CLI)
- A GCP project with billing enabled

## Quick Start

### 1. Enable GCP APIs & Set IAM Roles

```bash
bash scripts/setup_gcp.sh
```

### 2. Configure Secrets

```bash
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your project details
```

### 3. Authenticate

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Provision Agents from Config

```bash
# Upload config to GCS first
python -m scripts.upload_config_to_gcs \
  --local-path config/agents_config.yaml \
  --gcs-uri gs://YOUR_BUCKET/config/agents_config.yaml

# Provision all agents
python -m scripts.provision_agents \
  --config-gcs-uri gs://YOUR_BUCKET/config/agents_config.yaml
```

### 6. Launch the Chat UI

```bash
streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Configuration

Agent definitions live in `config/agents_config.yaml`. Each agent entry specifies:

| Field | Description |
|---|---|
| `agent_id` | Unique identifier for the CA API agent |
| `display_name` | Human-readable name shown in UI |
| `datasources[]` | BigQuery table references |
| `prompt_config` | How to generate the system instruction |
| `dataplex` | Optional Dataplex glossary link |
| `options` | Python analysis, stateful chat, etc. |
| `iam_bindings` | IAM roles to share the agent |

See the YAML file for full schema documentation.

## Project Structure

```
bq-analytics-agent/
├── config/                   # Agent definitions & templates
├── src/                      # Core Python modules
│   ├── config_loader.py      # Load agent config from GCS
│   ├── metadata_loader.py    # Load BQ/Dataplex metadata from GCS
│   ├── prompt_generator.py   # Generate LLM system instructions
│   ├── agent_manager.py      # CRUD for CA API DataAgents
│   ├── conversation_manager.py # Chat & conversation lifecycle
│   └── response_handler.py   # Parse streaming responses
├── ui/                       # Streamlit Chat Application
├── scripts/                  # CLI provisioning & setup scripts
├── deploy/                   # Docker & Cloud Run deployment
└── tests/                    # Unit tests
```

## Deployment to Cloud Run

```bash
# Build & deploy via Cloud Build
gcloud builds submit --config deploy/cloudbuild.yaml .
```

## License

Apache 2.0
