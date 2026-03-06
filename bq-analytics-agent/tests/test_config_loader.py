"""
Tests for src/config_loader.py
"""

from __future__ import annotations

import textwrap

import pytest

from src.config_loader import (
    AgentConfig,
    AgentsConfig,
    DatasourceConfig,
    GlobalConfig,
    PromptConfig,
    _parse_yaml,
    load_config_from_file,
)


# ── Sample YAML ──────────────────────────────────────────

VALID_YAML = textwrap.dedent("""\
    global:
      project_id: "test-project"
      location: "global"
      gcs_bucket: "test-bucket"
      metadata_base_path: "meta/"

    agents:
      - agent_id: "agent_1"
        display_name: "Test Agent"
        description: "A test agent"
        prompt_config:
          agent_name: "Test Bot"
          domain: "Testing"
          metadata_gcs_path: "test_metadata.json"
        datasources:
          - type: "bigquery"
            project_id: "test-project"
            dataset_id: "test_dataset"
            table_id: "test_table"
        options:
          python_analysis_enabled: true
          stateful_chat: true
""")

MINIMAL_YAML = textwrap.dedent("""\
    global:
      project_id: "proj"
      location: "global"
      gcs_bucket: "bucket"

    agents:
      - agent_id: "a1"
        display_name: "A1"
        prompt_config:
          agent_name: "Bot"
          domain: "D"
          metadata_gcs_path: "m.json"
        datasources:
          - project_id: "proj"
            dataset_id: "ds"
            table_id: "tbl"
""")

INVALID_YAML_NO_PROMPT_SOURCE = textwrap.dedent("""\
    global:
      project_id: "proj"
      location: "global"
      gcs_bucket: "bucket"

    agents:
      - agent_id: "bad"
        display_name: "Bad"
        prompt_config:
          agent_name: "Bot"
          domain: "D"
        datasources:
          - project_id: "proj"
            dataset_id: "ds"
            table_id: "tbl"
""")


# ── Tests ─────────────────────────────────────────────────


class TestParseYaml:
    def test_valid_full_config(self):
        config = _parse_yaml(VALID_YAML)
        assert isinstance(config, AgentsConfig)
        assert config.global_config.project_id == "test-project"
        assert config.global_config.gcs_bucket == "test-bucket"
        assert len(config.agents) == 1

        agent = config.agents[0]
        assert agent.agent_id == "agent_1"
        assert agent.display_name == "Test Agent"
        assert agent.prompt_config.agent_name == "Test Bot"
        assert agent.prompt_config.metadata_gcs_path == "test_metadata.json"
        assert len(agent.datasources) == 1
        assert agent.datasources[0].dataset_id == "test_dataset"
        assert agent.options.python_analysis_enabled is True

    def test_minimal_config(self):
        config = _parse_yaml(MINIMAL_YAML)
        assert len(config.agents) == 1
        agent = config.agents[0]
        assert agent.description == ""
        assert agent.options.python_analysis_enabled is False
        assert agent.options.stateful_chat is True  # default

    def test_invalid_no_prompt_source_raises(self):
        with pytest.raises(Exception):
            _parse_yaml(INVALID_YAML_NO_PROMPT_SOURCE)

    def test_global_config_alias(self):
        config = _parse_yaml(VALID_YAML)
        assert isinstance(config.global_config, GlobalConfig)


class TestLoadFromFile:
    def test_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(Exception):
            load_config_from_file(tmp_path / "nope.yaml")

    def test_valid_file(self, tmp_path):
        f = tmp_path / "agents.yaml"
        f.write_text(VALID_YAML, encoding="utf-8")
        config = load_config_from_file(f)
        assert config.global_config.project_id == "test-project"
