# BigQuery Conversational Analytics Agent System - Implementation Plan

## Overview

Build a dynamic, config-driven system that programmatically creates BigQuery Data Analytics Agents using the Conversational Analytics (CA) API Python SDK. The system reads agent definitions from a JSON config in GCS, generates LLM system prompts from Dataplex/BQ metadata, provisions agents via the CA API, and provides a chat UI that mimics the BigQuery Console agent experience.

---

## Architecture

```
GCS Config Bucket
  ├── agents_config.json          (agent definitions: which agents to create)
  └── metadata/
      └── <agent_id>_metadata.json  (per-agent BQ + Dataplex metadata)
          │
          ▼
┌──────────────────────────────────┐
│  1. Config Loader (config/)      │  Reads agent configs from GCS
│  2. Prompt Generator (prompts/)  │  Generates LLM instructions from metadata
│  3. Agent Provisioner (agents/)  │  Creates/updates CA API agents
│  4. Chat Service (chat/)         │  Conversation + streaming chat
│  5. Web UI (ui/)                 │  Streamlit app mimicking BQ Console
└──────────────────────────────────┘
          │
          ▼
   Google Cloud CA API
   (DataAgentServiceClient / DataChatServiceClient)
```

---

## Project Structure

```
bq_agent_system/
├── config/
│   ├── __init__.py
│   ├── loader.py              # Load agent configs from GCS
│   └── schema.py              # Pydantic models for config validation
├── prompts/
│   ├── __init__.py
│   └── generator.py           # LLM system prompt generator (from notebook)
├── agents/
│   ├── __init__.py
│   └── provisioner.py         # Create/update/delete CA API agents
├── chat/
│   ├── __init__.py
│   └── service.py             # Conversation creation + streaming chat
├── ui/
│   └── app.py                 # Streamlit chat UI
├── sample_configs/
│   ├── agents_config.json     # Example multi-agent config
│   └── ordertake_metadata.json # Copy of the provided metadata JSON
├── scripts/
│   ├── provision_agents.py    # CLI script: provision all agents from config
│   └── setup_gcp.sh           # Enable APIs + install deps
├── requirements.txt
├── Dockerfile                 # For Cloud Run deployment
└── README.md                  # Not created unless requested
```

---

## Step-by-Step Implementation

### Step 1: Config Schema & Loader (`config/`)

**Files:** `config/schema.py`, `config/loader.py`

**Config schema** (`agents_config.json` in GCS):
```json
{
  "project_id": "ordertake-datalake-gcp-pilot",
  "location": "global",
  "gcs_bucket": "ordertake-datalake-gcp-pilot-landing",
  "agents": [
    {
      "agent_id": "ordertake_agent_v2",
      "display_name": "Ordertake_Agent",
      "description": "BigQuery conversation agent for Ordertake Performance Data",
      "metadata_file": "4_business_glossary_and_KPI_Dataplex_vs_BigQuery.json",
      "datasources": [
        {
          "project_id": "ordertake-datalake-gcp-pilot",
          "dataset_id": "gold_business",
          "table_id": "gold_kpi_unified"
        }
      ],
      "dataplex_glossary": {
        "project_id": "ordertake-datalake-gcp-pilot",
        "location": "us",
        "glossary_id": "ot-glossary-v6"
      },
      "prompt_settings": {
        "agent_name": "Ordertake Agent",
        "domain": "Automotive Order Take"
      },
      "labels": {},
      "max_bytes_billed": 0
    }
  ]
}
```

**Required variables/inputs per agent** (extracted from all support files):
- `agent_id` — unique CA API agent identifier
- `display_name` — human-readable name (shown in console)
- `description` — agent purpose description
- `project_id` — GCP project hosting the agent
- `location` — CA API location (`global`)
- `datasources[]` — list of BigQuery table references:
  - `project_id`, `dataset_id`, `table_id`
- `metadata_file` — GCS path to the JSON metadata file containing:
  - `config.dataset`, `config.table`
  - `bigquery_technical_metadata.description`
  - `bigquery_technical_metadata.columns{}` (name, description, data_type_hint, example_values, calculation_logic)
  - `dataplex_business_glossary.terms[]` (business_term, definition, linked_assets, data_steward, update_frequency, security_classification)
- `dataplex_glossary` — reference to Dataplex glossary (project, location, glossary_id)
- `prompt_settings.agent_name` — name used in system prompt
- `prompt_settings.domain` — business domain for the prompt
- `labels` — optional key-value labels for cost tracking
- `max_bytes_billed` — BigQuery billing limit

**Pydantic models** validate all the above at load time.

### Step 2: LLM Prompt Generator (`prompts/`)

**File:** `prompts/generator.py`

Port the logic from `dataplex_llm_prompt_generator.ipynb` into a reusable module:
- `generate_llm_system_prompt(metadata, agent_name, domain) -> str`
- Reads BQ technical metadata (columns, types, descriptions)
- Maps Dataplex business glossary terms to columns
- Produces the full system prompt matching the format in `LLM_prompt_generated_from_dataplex_llm_prompt_generator.txt`
- Includes: schema block, business term dictionary, rules, response format

### Step 3: Agent Provisioner (`agents/`)

**File:** `agents/provisioner.py`

Uses `google.cloud.geminidataanalytics` SDK:
- `provision_agent(agent_config, system_prompt) -> DataAgent`
  - Builds `BigQueryTableReference` with `Schema` and `Field` objects per column
  - Builds `DatasourceReferences` linking tables
  - Creates `Context` with `system_instruction` = generated prompt
  - Creates `DataAgent` with `DataAnalyticsAgent.published_context`
  - Calls `DataAgentServiceClient.create_data_agent()`
- `provision_all_agents(config) -> list[DataAgent]`
  - Iterates over all agents in config
  - For each: load metadata from GCS → generate prompt → provision agent
- `list_agents(project_id, location) -> list`
- `delete_agent(agent_name) -> None`
- `update_agent(agent_config, system_prompt) -> DataAgent`
- Handles idempotency: check if agent exists before creating (update if exists)

### Step 4: Chat Service (`chat/`)

**File:** `chat/service.py`

- `create_conversation(project_id, location, agent_name) -> Conversation`
- `send_message(conversation_name, agent_name, question) -> generator`
  - Yields streaming response chunks (text, SQL, data, chart specs)
  - Parses `SystemMessage` types: THOUGHT, PROGRESS, ANSWER, ERROR
- `ChatSession` class — wraps stateful conversation for the UI:
  - Manages conversation lifecycle
  - Tracks message history
  - Provides typed response objects for UI rendering

### Step 5: Streamlit Chat UI (`ui/app.py`)

Mimics the BigQuery Console agent chat experience (as seen in screenshots):

**Layout:**
- Left sidebar: Agent selector (dropdown of provisioned agents), agent info
- Main area: Chat interface with message history
- Message bubbles: user questions (right), agent responses (left)
- Agent responses include:
  - Natural language answer text
  - Expandable SQL query block
  - Data table (rendered via `st.dataframe`)
  - Vega-Lite chart (rendered via `st.vega_lite_chart`)
  - Thinking/progress indicators during streaming

**Features:**
- Agent selection from provisioned agents
- Real-time streaming responses
- Conversation history maintained in session state
- "New conversation" button
- Display of agent metadata (description, knowledge sources, glossary terms)

### Step 6: CLI Script & Setup (`scripts/`)

**`scripts/setup_gcp.sh`:**
- Enable required APIs: `geminidataanalytics`, `bigquery`, `cloudaicompanion`, `dataplex`
- Install Python dependencies

**`scripts/provision_agents.py`:**
- CLI entry point: `python provision_agents.py --config gs://bucket/agents_config.json`
- Loads config → provisions all agents → prints summary
- Supports `--dry-run` flag to preview without creating

### Step 7: Deployment (`Dockerfile`, `requirements.txt`)

**`requirements.txt`:**
```
google-cloud-geminidataanalytics>=0.1.0
google-cloud-storage>=2.10.0
google-cloud-dataplex>=2.0.0
google-cloud-bigquery>=3.11.0
streamlit>=1.28.0
pydantic>=2.0.0
```

**`Dockerfile`:**
- Python 3.11 slim base
- Install requirements
- Expose port 8501 (Streamlit default)
- Entry point: `streamlit run ui/app.py`

---

## Key Design Decisions

1. **Config-driven**: All agent definitions live in a single JSON config in GCS. Adding a new agent = adding an entry to the JSON + uploading its metadata file.
2. **Metadata reuse**: The same JSON metadata format (BQ technical + Dataplex glossary) drives both prompt generation and agent schema fields.
3. **Idempotent provisioning**: The provisioner checks for existing agents and updates rather than failing on duplicates.
4. **Streaming-first chat**: The chat service yields response chunks for real-time UI updates.
5. **Streamlit UI**: Lightweight, Python-native, fast to build, and can be deployed to Cloud Run easily.

---

## Execution Order

1. `config/schema.py` — Pydantic models
2. `config/loader.py` — GCS config loader
3. `prompts/generator.py` — System prompt generator
4. `agents/provisioner.py` — CA API agent provisioner
5. `chat/service.py` — Chat/conversation service
6. `ui/app.py` — Streamlit chat UI
7. `sample_configs/` — Example config files
8. `scripts/` — CLI tools and setup
9. `requirements.txt` + `Dockerfile` — Packaging
