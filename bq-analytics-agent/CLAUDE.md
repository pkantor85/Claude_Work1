# CLAUDE.md — Project Guide for AI Agents

## Project Overview

**BigQuery Data Analytics Agent System** — A production-grade system for programmatically creating and managing domain-specific BigQuery Data Agents using Google Cloud's **Conversational Analytics (CA) API**. Agents are dynamically provisioned from YAML configuration stored in GCS, with system instructions auto-generated from Dataplex/BigQuery metadata.

## Tech Stack

- **Language**: Python 3.11+
- **Core SDK**: `google-cloud-geminidataanalytics` (Conversational Analytics API)
- **Cloud Services**: BigQuery, Cloud Storage (GCS), Dataplex, Cloud Run, Cloud Build
- **UI**: Streamlit (multi-page app)
- **Validation**: Pydantic v2
- **Visualization**: Altair / Vega-Lite
- **Config format**: YAML (`config/agents_config.yaml`)
- **Testing**: pytest with mocks (no live GCP calls in tests)

## Project Structure

```text
bq-analytics-agent/
├── config/agents_config.yaml        # Master agent registry (agents, datasources, prompts)
├── src/                             # Core library
│   ├── utils.py                     # Logging, auth helpers
│   ├── config_loader.py             # Load & validate YAML config from GCS/local (Pydantic models)
│   ├── metadata_loader.py           # Parse BQ/Dataplex metadata JSON
│   ├── prompt_generator.py          # Generate LLM system instructions from metadata
│   ├── agent_manager.py             # CRUD for CA API DataAgents (create/get/list/update/delete)
│   ├── conversation_manager.py      # Conversation lifecycle & chat streaming
│   └── response_handler.py          # Parse streaming responses (text/data/chart/schema)
├── ui/                              # Streamlit multi-page app
│   ├── app.py                       # Entry point, sidebar, session state
│   ├── pages/
│   │   ├── 1_🤖_Agent_Management.py # Agent CRUD forms
│   │   ├── 2_💬_Chat.py             # BigQuery Console-like chat interface
│   │   └── 3_📜_History.py          # Browse/resume past conversations
│   ├── components/                  # Reusable Streamlit components
│   │   ├── chart_renderer.py        # Altair/Vega-Lite chart rendering
│   │   ├── chat_message.py          # Chat bubble UI
│   │   ├── data_table.py            # DataFrame display
│   │   └── sql_display.py           # SQL syntax-highlighted display
│   └── styles/custom.css            # Google Cloud-inspired styling
├── scripts/                         # CLI utilities
│   ├── provision_agents.py          # Bulk provision agents from config
│   ├── upload_config_to_gcs.py      # Upload local files to GCS
│   ├── setup_gcp.ps1                # PowerShell: enable APIs, set IAM roles
│   └── setup_gcp.sh                 # Bash: enable APIs, set IAM roles
├── deploy/                          # Cloud Run deployment
│   ├── Dockerfile                   # Python 3.11-slim, Streamlit on port 8080
│   ├── cloudbuild.yaml              # 3-step CI/CD pipeline
│   └── cloudrun_service.yaml        # Knative service spec (autoscale 0-3)
├── tests/                           # Unit tests (all mocked, no live GCP)
│   ├── test_config_loader.py        # YAML parsing, Pydantic validation
│   ├── test_prompt_generator.py     # System instruction generation
│   ├── test_agent_manager.py        # Mocked SDK CRUD operations
│   └── test_conversation_manager.py # Mocked chat/conversation lifecycle
├── conftest.py                      # Adds project root to sys.path for tests
├── pyproject.toml                   # Build config, pytest/ruff settings
├── requirements.txt                 # All Python dependencies
├── setup.py                         # Editable install support
└── Makefile                         # Common dev commands
```

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run Streamlit UI locally
streamlit run ui/app.py

# Provision agents from local config
python -m scripts.provision_agents --config-local config/agents_config.yaml

# Provision agents from GCS config
python -m scripts.provision_agents --config-gcs-uri gs://BUCKET/config/agents_config.yaml

# Upload config to GCS
python -m scripts.upload_config_to_gcs --local-path config/agents_config.yaml --gcs-uri gs://BUCKET/config/agents_config.yaml

# Deploy to Cloud Run
gcloud builds submit --config deploy/cloudbuild.yaml .

# GCP setup (Windows PowerShell)
$env:PROJECT_ID = "ordertake-datalake-gcp-pilot"
.\scripts\setup_gcp.ps1
```

## Import Conventions

All core modules use `from src.<module>` imports:

```python
from src.utils import get_logger
from src.config_loader import AgentsConfig, load_config_from_gcs
from src.metadata_loader import parse_metadata, load_metadata_from_gcs
from src.prompt_generator import generate_system_instruction
from src.agent_manager import create_agent, list_agents, provision_all_agents
from src.conversation_manager import create_conversation, send_message_stateful
from src.response_handler import parse_stream_message, AgentResponse
```

## Key Pydantic Models (src/config_loader.py)

- `AgentsConfig` — Top-level: `global` (GlobalConfig) + `agents` list
- `AgentConfig` — Per-agent: agent_id, display_name, prompt_config, datasources, etc.
- `GlobalConfig` — project_id, location, gcs_bucket, metadata_base_path
- `PromptConfig` — agent_name, domain, metadata_gcs_path OR prompt_gcs_path
- `DatasourceConfig` — type, project_id, dataset_id, table_id

## Key Data Classes (src/response_handler.py)

- `AgentResponse` — Typed parsed response with `response_type` (TEXT/SCHEMA/DATA/CHART)
- `TextType` — THOUGHT, PROGRESS, FINAL_RESPONSE
- Response data can be: plain text, SQL string, pandas DataFrame, or Vega chart dict

## Configuration

The master config lives at `config/agents_config.yaml`. Key structure:

```yaml
global:
  project_id: "ordertake-datalake-gcp-pilot"
  location: "global"
  gcs_bucket: "ordertake-datalake-gcp-pilot-landing"
  metadata_base_path: "agent_metadata/"

agents:
  - agent_id: "ordertake_agent_v2"
    display_name: "Ordertake Performance Agent"
    prompt_config:
      agent_name: "Ordertake Agent"
      domain: "Automotive Order Take"
      metadata_gcs_path: "4_business_glossary_and_KPI_Dataplex_vs_BigQuery.json"
    datasources:
      - type: "bigquery"
        project_id: "ordertake-datalake-gcp-pilot"
        dataset_id: "gold_business"
        table_id: "gold_kpi_unified"
```

Streamlit secrets go in `.streamlit/secrets.toml` (not committed).

## GCP Project Details

- **Project ID**: `ordertake-datalake-gcp-pilot`
- **GCS Bucket**: `ordertake-datalake-gcp-pilot-landing`
- **Dataset**: `gold_business.gold_kpi_unified`
- **Dataplex Glossary**: `ot-glossary-v6` (location: `us`)
- **Column naming convention**: `DIM_*` for dimensions, `M_*` for measures

## Required GCP APIs

- `geminidataanalytics.googleapis.com`
- `bigquery.googleapis.com`
- `cloudaicompanion.googleapis.com`
- `dataplex.googleapis.com`
- `storage.googleapis.com`
- `run.googleapis.com`
- `cloudbuild.googleapis.com`

## Testing Strategy

- All tests use `unittest.mock` / `pytest-mock` — **no live GCP calls**
- CA API clients (`DataAgentServiceClient`, `DataChatServiceClient`) are always mocked
- Test files mirror `src/` modules: `test_<module>.py`
- `conftest.py` ensures `src.*` imports resolve from project root
- Run: `pytest tests/ -v`

## Code Style

- **Line length**: 88 (ruff)
- **Target version**: Python 3.11
- **Linting rules**: E, F, I, W (via ruff)
- **Docstrings**: Module-level and function-level docstrings on all public APIs
- **Type hints**: All function signatures use type annotations
- **Logging**: Use `get_logger(__name__)` from `src.utils` — never bare `print()`

## Architecture Patterns

- **Config-driven provisioning**: Agents are defined in YAML, not code. Adding an agent = adding a YAML block.
- **Singleton clients**: `agent_manager.py` uses module-level `_agent_client` / `_chat_client` initialized on first use.
- **Streaming responses**: Chat uses server-sent streaming; `response_handler.py` classifies each chunk.
- **Metadata → Prompt pipeline**: JSON metadata (BQ schema + Dataplex glossary) → `prompt_generator.py` → system instruction text.
- **Session state**: Streamlit `st.session_state` stores project_id, active agent, conversation, and chat history.
