"""
prompt_generator — Generate LLM system instructions from metadata.

Adapted from ``dataplex_llm_prompt_generator.ipynb``.  Takes a
:class:`MetadataBundle` (parsed from the GCS JSON) plus agent-level
configuration and produces the full system prompt that is injected into
the CA API agent's *Instructions* field.
"""

from __future__ import annotations

from src.metadata_loader import MetadataBundle
from src.utils import get_logger

logger = get_logger(__name__)


def generate_system_instruction(
    metadata: MetadataBundle,
    agent_name: str = "SQL Assistant",
    domain: str = "Data Analytics",
) -> str:
    """
    Build a complete system instruction for a Text-to-SQL agent.

    The prompt follows the structure recommended by Google's CA API
    documentation and mirrors the output of the original
    ``dataplex_llm_prompt_generator.ipynb`` notebook:

    1. Role declaration
    2. Database schema (table + columns)
    3. Business term dictionary
    4. Formatting and behaviour rules
    5. Response format guidance

    Parameters
    ----------
    metadata:
        The parsed metadata bundle containing schema and glossary data.
    agent_name:
        The persona name injected into the prompt.
    domain:
        Business domain description.

    Returns
    -------
    str
        Ready-to-use system instruction text.
    """
    dataset = metadata.dataset
    table = metadata.table
    table_desc = metadata.table_description

    # ── Column schema ──────────────────────────────────────
    schema_lines: list[str] = []
    for col in metadata.columns:
        schema_lines.append(
            f"  - {col.name} ({col.data_type_hint}): {col.description}"
        )
    schema_str = "\n".join(schema_lines)

    # ── Business term dictionary ───────────────────────────
    term_lines: list[str] = []
    for term in metadata.business_terms:
        linked = term.linked_assets
        col = linked[0].split(".")[-1] if linked else "N/A"
        term_lines.append(
            f'  - "{term.business_term}" → Column: {col} | '
            f"{term.definition}"
        )
    terms_str = "\n".join(term_lines)

    # ── Calculation logic notes (if available) ─────────────
    calc_lines: list[str] = []
    for col in metadata.columns:
        if col.calculation_logic:
            calc_lines.append(
                f"  - {col.name}: {col.calculation_logic}"
            )
    calc_section = ""
    if calc_lines:
        calc_section = (
            "\nCALCULATION LOGIC NOTES:\n"
            + "\n".join(calc_lines)
            + "\n"
        )

    # ── Assemble prompt ────────────────────────────────────
    prompt = f"""\
You are {agent_name}, a SQL Assistant specialized in {domain} datasets.

YOUR TASK:
Convert natural language questions into valid BigQuery SQL queries.

DATABASE SCHEMA:
Table: `{dataset}.{table}`
Description: {table_desc}

Columns:
{schema_str}

BUSINESS TERM DICTIONARY:
When users mention these business terms, map them to the corresponding columns:
{terms_str}
{calc_section}
IMPORTANT RULES:
1. Columns starting with 'DIM_' are dimensions; 'M_' are metrics.
2. **CRITICAL:** Always treat DIM_YEARMONTH as a String. Never format it with thousands separators (commas).
3. **OUTPUT LIMITATION:** Do not display the raw technical query result or a "Data Analysis" preview table. Only provide the final formatted "Tabular View" and "Chart View (if applicable)" described in the response format below.
4. Pre-calculated KPI columns must be used directly instead of recalculating.
5. Always qualify the table with the full path: `{dataset}.{table}`

RESPONSE FORMAT:
When asked a question: Provide the valid BigQuery SQL query.
"""
    logger.info(
        "Generated system instruction for agent '%s' (%d chars)",
        agent_name,
        len(prompt),
    )
    return prompt
