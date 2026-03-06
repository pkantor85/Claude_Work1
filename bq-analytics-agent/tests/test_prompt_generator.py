"""
Tests for src/prompt_generator.py
"""

from __future__ import annotations

import pytest

from src.metadata_loader import (
    BusinessTerm,
    ColumnMeta,
    MetadataBundle,
    parse_metadata,
)
from src.prompt_generator import generate_system_instruction


# ── Fixtures ──────────────────────────────────────────────

SAMPLE_RAW_METADATA = {
    "config": {"dataset": "gold_business", "table": "gold_kpi_unified"},
    "bigquery_technical_metadata": {
        "description": "Ordertake performance data.",
        "columns": {
            "DIM_YEARMONTH": {
                "description": "Year and month identifier.",
                "data_type_hint": "String (YYYYMM)",
                "calculation_logic": "Derived from ROAR_DATE.",
            },
            "M_OT_ACT": {
                "description": "Actual order count.",
                "data_type_hint": "Integer (Count)",
                "example_values": ["0", "42"],
            },
        },
    },
    "dataplex_business_glossary": {
        "terms": [
            {
                "business_term": "Performance Period",
                "definition": "The fiscal reporting month.",
                "linked_assets": ["gold_kpi_unified.DIM_YEARMONTH"],
            },
            {
                "business_term": "Ordertake Actual",
                "definition": "Confirmed volume of orders.",
                "linked_assets": ["gold_kpi_unified.M_OT_ACT"],
            },
        ]
    },
}


@pytest.fixture
def metadata() -> MetadataBundle:
    return parse_metadata(SAMPLE_RAW_METADATA)


# ── Tests ─────────────────────────────────────────────────


class TestGenerateSystemInstruction:
    def test_contains_agent_name(self, metadata):
        prompt = generate_system_instruction(
            metadata, agent_name="Test Agent", domain="Testing"
        )
        assert "Test Agent" in prompt

    def test_contains_domain(self, metadata):
        prompt = generate_system_instruction(
            metadata, agent_name="Bot", domain="Automotive Order Take"
        )
        assert "Automotive Order Take" in prompt

    def test_contains_table_reference(self, metadata):
        prompt = generate_system_instruction(metadata)
        assert "gold_business.gold_kpi_unified" in prompt

    def test_contains_column_names(self, metadata):
        prompt = generate_system_instruction(metadata)
        assert "DIM_YEARMONTH" in prompt
        assert "M_OT_ACT" in prompt

    def test_contains_business_terms(self, metadata):
        prompt = generate_system_instruction(metadata)
        assert "Performance Period" in prompt
        assert "Ordertake Actual" in prompt

    def test_contains_rules(self, metadata):
        prompt = generate_system_instruction(metadata)
        assert "DIM_" in prompt
        assert "CRITICAL" in prompt

    def test_contains_calculation_logic(self, metadata):
        prompt = generate_system_instruction(metadata)
        assert "CALCULATION LOGIC" in prompt
        assert "Derived from ROAR_DATE" in prompt

    def test_output_is_string(self, metadata):
        prompt = generate_system_instruction(metadata)
        assert isinstance(prompt, str)
        assert len(prompt) > 100


class TestParseMetadata:
    def test_basic_parsing(self):
        bundle = parse_metadata(SAMPLE_RAW_METADATA)
        assert bundle.dataset == "gold_business"
        assert bundle.table == "gold_kpi_unified"
        assert len(bundle.columns) == 2
        assert len(bundle.business_terms) == 2

    def test_column_attributes(self):
        bundle = parse_metadata(SAMPLE_RAW_METADATA)
        dim_col = next(c for c in bundle.columns if c.name == "DIM_YEARMONTH")
        assert dim_col.data_type_hint == "String (YYYYMM)"
        assert dim_col.calculation_logic == "Derived from ROAR_DATE."

    def test_business_term_attributes(self):
        bundle = parse_metadata(SAMPLE_RAW_METADATA)
        term = next(
            t for t in bundle.business_terms
            if t.business_term == "Performance Period"
        )
        assert "fiscal reporting" in term.definition
        assert "DIM_YEARMONTH" in term.linked_assets[0]

    def test_empty_metadata(self):
        bundle = parse_metadata({})
        assert bundle.dataset == "unknown_dataset"
        assert bundle.table == "unknown_table"
        assert bundle.columns == []
        assert bundle.business_terms == []
