# CLAUDE.md — AI Assistant Guide for Claude_Work1

## Project Overview

This repository is a **documentation and setup guide** for creating conversational AI agents on Google Cloud Platform (GCP). It focuses on enabling natural language to BigQuery SQL conversion for Ordertake performance tracking in the automotive industry.

The project demonstrates how to:
- Generate LLM system prompts dynamically from Dataplex business glossaries
- Create GCP Gemini Data Analytics agents via the Python SDK
- Enable stateful, SQL-capable conversations over BigQuery data

---

## Repository Structure

```
Claude_Work1/
├── CLAUDE.md                          # This file
├── .gitattributes                     # Git line-ending config (text=auto)
└── support_files/
    ├── 4_business_glossary_and_KPI_Dataplex_vs_BigQuery.json   # Column metadata and glossary
    ├── dataplex_llm_prompt_generator.ipynb                     # Notebook: generates system prompts
    ├── LLM_prompt_generated_from_dataplex_llm_prompt_generator.txt  # Generated agent system prompt
    ├── Programmatic_Agent_Creation_example.txt                 # Python SDK usage guide
    ├── BQ_Agent_Console_Example_1.webp                         # UI screenshot
    ├── BQ_Agent_Console_Example_2.webp                         # UI screenshot
    └── BQ_Agent_Console_Example_3.webp                         # UI screenshot
```

---

## Key Files Explained

### `support_files/4_business_glossary_and_KPI_Dataplex_vs_BigQuery.json`
JSON metadata file containing:
- BigQuery column definitions for the `gold_business.gold_kpi_unified` table
- Dataplex business glossary entries
- Business term mappings, example values, and KPI calculation logic
- Data steward and business function context

**Dimensions:** `DIM_YEARMONTH`, `DIM_MARKET_NAME`, `DIM_MAIN_CHANNEL`, `DIM_MODEL_NAME`
**Metrics:** `M_OT_ACT`, `M_CAL_OT_OBJ`, `M_PERF_VS_CALOBJ`

### `support_files/dataplex_llm_prompt_generator.ipynb`
Jupyter Notebook that:
- Reads metadata from GCS and Dataplex API
- Generates a structured LLM system prompt via `generate_llm_system_prompt()`
- Outputs the prompt to `LLM_prompt_generated_from_dataplex_llm_prompt_generator.txt`

Key configuration variables in the notebook:
```python
PROJECT_ID  = "ordertake-datalake-gcp-pilot"
LOCATION    = "global"          # or "us" depending on context
GLOSSARY_ID = "ot-glossary-v6"
BUCKET_NAME = "ordertake-datalake-gcp-pilot-landing"
```

### `support_files/LLM_prompt_generated_from_dataplex_llm_prompt_generator.txt`
The complete system prompt used by the Ordertake Agent. Contains:
- Database schema definition
- Column descriptions and business rules
- Natural language to SQL conversion guidelines
- Response format specifications

### `support_files/Programmatic_Agent_Creation_example.txt`
Step-by-step Python code for creating the agent via the Gemini Data Analytics API:
- GCP service enablement (`gcloud` commands)
- Python SDK installation: `pip install google-cloud-geminidataanalytics google-cloud-dataplex google-cloud-storage`
- Agent creation with BigQuery table references
- Stateful conversation and streaming chat setup

---

## GCP Infrastructure

| Resource        | Value                                       |
|-----------------|---------------------------------------------|
| Project ID      | `ordertake-datalake-gcp-pilot`              |
| BigQuery Dataset| `gold_business`                             |
| BigQuery Table  | `gold_kpi_unified`                          |
| Dataplex Glossary | `ot-glossary-v6`                          |
| GCS Bucket      | `ordertake-datalake-gcp-pilot-landing`      |
| Location        | `global` / `us`                             |

---

## Development Workflow

### Running the Notebook
1. Ensure GCP authentication is configured: `gcloud auth application-default login`
2. Install required Python packages:
   ```bash
   pip install google-cloud-geminidataanalytics google-cloud-dataplex google-cloud-storage
   ```
3. Open and run `support_files/dataplex_llm_prompt_generator.ipynb` in Jupyter
4. The generated system prompt will be written to `LLM_prompt_generated_from_dataplex_llm_prompt_generator.txt`

### Creating an Agent Programmatically
Follow the code examples in `support_files/Programmatic_Agent_Creation_example.txt`. Key steps:
1. Enable GCP APIs via `gcloud services enable`
2. Create an agent instance pointing to the BigQuery table
3. Initialize a stateful session
4. Send queries using the streaming chat interface

---

## Conventions and Guidelines for AI Assistants

### What This Repo Is (and Is Not)
- **Is:** A documentation, configuration, and example-code repository
- **Is not:** A deployable application with source code, tests, or a build system
- There are no unit tests, CI/CD pipelines, linters, or build scripts — do not add them unless explicitly requested

### When Updating Files
- **JSON metadata** (`4_business_glossary_and_KPI_Dataplex_vs_BigQuery.json`): Keep structure consistent with existing schema. Preserve all existing keys when adding new entries.
- **System prompt** (`LLM_prompt_generated_from_dataplex_llm_prompt_generator.txt`): This is a generated output. Prefer updating the notebook and re-running rather than editing the output directly.
- **Notebook** (`dataplex_llm_prompt_generator.ipynb`): Edit cells carefully; preserve existing cell outputs unless intentionally refreshing them.
- **Example code** (`Programmatic_Agent_Creation_example.txt`): Keep examples runnable and consistent with the installed SDK version.

### Adding New Content
- Place all new files under `support_files/` unless they are repo-level documentation
- Screenshots or UI examples go in `support_files/` as `.webp` or `.png`
- Do not create top-level directories without a clear reason

### Environment/Credentials
- No `.env` files are tracked in this repo
- Configuration values (project IDs, bucket names, etc.) are currently hardcoded in examples — this is intentional for clarity
- Never commit real credentials or service account keys

### Commit Messages
Follow the pattern used in existing commits:
- Short, imperative, capitalized: `Add new glossary entries for Q4 metrics`
- No period at end of subject line
- Reference the file or component changed when relevant

---

## No Active Tooling

This repository has **no** active:
- Test runner (`pytest`, `jest`, etc.)
- Linter or formatter (`flake8`, `black`, `eslint`, etc.)
- Pre-commit hooks
- CI/CD pipelines

Do not assume these exist or need to be run before committing.
