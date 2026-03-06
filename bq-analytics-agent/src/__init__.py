"""
BigQuery Data Analytics Agent — Core Library.

Provides modules for:
- config_loader:       Load agent configuration from GCS (YAML)
- metadata_loader:     Load BQ/Dataplex metadata from GCS (JSON)
- prompt_generator:    Generate LLM system instructions from metadata
- agent_manager:       CRUD operations for CA API DataAgents
- conversation_manager: Conversation lifecycle & chat streaming
- response_handler:    Parse text/data/chart/schema streaming responses
- utils:               Shared helpers (auth, logging)
"""

__version__ = "1.0.0"
