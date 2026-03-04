"""Generate LLM system prompts from BigQuery + Dataplex metadata.

Ported from support_files/dataplex_llm_prompt_generator.ipynb.
"""

from __future__ import annotations

from typing import Any


def generate_llm_system_prompt(
    metadata: dict[str, Any],
    agent_name: str = "SQL Assistant",
    domain: str = "Data Analytics",
) -> str:
    """Generate a complete system prompt for a Text-to-SQL CA API agent.

    The prompt includes schema structure, business term mappings,
    usage rules, and response format instructions.

    Args:
        metadata: Parsed metadata dictionary containing ``config``,
            ``bigquery_technical_metadata``, and ``dataplex_business_glossary``.
        agent_name: Display name for the agent persona.
        domain: Business domain description.

    Returns:
        Full system instruction string ready for the CA API agent.
    """
    config = metadata.get("config", {})
    tech_meta = metadata.get("bigquery_technical_metadata", {})
    glossary = metadata.get("dataplex_business_glossary", {})

    dataset = config.get("dataset", "unknown_dataset")
    table = config.get("table", "unknown_table")
    table_desc = tech_meta.get("description", "")
    columns = tech_meta.get("columns", {})
    terms = glossary.get("terms", [])

    schema_str = _build_schema_block(columns)
    terms_str = _build_terms_block(terms)

    prompt = (
        f"You are {agent_name}, a SQL Assistant specialized in {domain} datasets.\n"
        f"\n"
        f"YOUR TASK:\n"
        f"Convert natural language questions into valid BigQuery SQL queries.\n"
        f"\n"
        f"DATABASE SCHEMA:\n"
        f"Table: `{dataset}.{table}`\n"
        f"Description: {table_desc}\n"
        f"\n"
        f"Columns:\n"
        f"{schema_str}\n"
        f"\n"
        f"BUSINESS TERM DICTIONARY:\n"
        f"When users mention these business terms, map them to the corresponding columns:\n"
        f"{terms_str}\n"
        f"\n"
        f"IMPORTANT RULES:\n"
        f"1. Columns starting with 'DIM_' are dimensions; 'M_' are metrics.\n"
        f"2. **CRITICAL:** Always treat DIM_YEARMONTH as a String. Never format it with thousands separators (commas).\n"
        f"3. **OUTPUT LIMITATION:** Do not display the raw technical query result or a \"Data Analysis\" preview table. "
        f"Only provide the final formatted \"Tabular View\" described in the response format below.\n"
        f"4. Pre-calculated KPI columns must be used directly instead of recalculating.\n"
        f"5. Always qualify the table with the full path: `{dataset}.{table}`\n"
        f"\n"
        f"\n"
        f"RESPONSE FORMAT:\n"
        f"When asked a question: Provide the valid BigQuery SQL query.\n"
    )

    return prompt


def _build_schema_block(columns: dict[str, Any]) -> str:
    """Build the column schema section of the prompt."""
    lines = []
    for col_name, col_meta in columns.items():
        desc = col_meta.get("description", "")
        dtype = col_meta.get("data_type_hint", "Unknown")
        lines.append(f"  - {col_name} ({dtype}): {desc}")
    return "\n".join(lines)


def _build_terms_block(terms: list[dict[str, Any]]) -> str:
    """Build the business term dictionary section of the prompt."""
    lines = []
    for term in terms:
        name = term.get("business_term", "")
        definition = term.get("definition", "")
        linked = term.get("linked_assets", [])
        col = linked[0].split(".")[-1] if linked else "N/A"
        lines.append(f'  - "{name}" -> Column: {col} | {definition}')
    return "\n".join(lines)
