"""
Tests for src/agent_manager.py

These tests mock the geminidataanalytics SDK to verify agent creation
logic without making actual API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.config_loader import (
    AgentConfig,
    AgentOptions,
    AgentsConfig,
    DatasourceConfig,
    GlobalConfig,
    PromptConfig,
)


@pytest.fixture
def global_cfg() -> GlobalConfig:
    return GlobalConfig(
        project_id="test-project",
        location="global",
        gcs_bucket="test-bucket",
    )


@pytest.fixture
def agent_cfg() -> AgentConfig:
    return AgentConfig(
        agent_id="test_agent",
        display_name="Test Agent",
        description="Test description",
        prompt_config=PromptConfig(
            agent_name="Test Bot",
            domain="Testing",
            metadata_gcs_path="test_meta.json",
        ),
        datasources=[
            DatasourceConfig(
                project_id="test-project",
                dataset_id="test_ds",
                table_id="test_tbl",
            )
        ],
        options=AgentOptions(
            python_analysis_enabled=True,
            stateful_chat=True,
        ),
    )


@pytest.fixture
def agents_config(global_cfg, agent_cfg) -> AgentsConfig:
    return AgentsConfig.model_validate({
        "global": global_cfg.model_dump(),
        "agents": [agent_cfg.model_dump()],
    })


class TestAgentManager:
    """Test agent_manager functions with mocked SDK clients."""

    @patch("src.agent_manager._get_agent_client")
    @patch("src.agent_manager._resolve_system_instruction")
    @patch("src.agent_manager._resolve_metadata")
    def test_create_agent_calls_sdk(
        self, mock_meta, mock_instr, mock_client_fn, agent_cfg, global_cfg
    ):
        mock_instr.return_value = "You are a test agent."
        mock_meta.return_value = None

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.name = (
            "projects/test-project/locations/global/dataAgents/test_agent"
        )
        mock_client.create_data_agent_sync.return_value = mock_response
        mock_client_fn.return_value = mock_client

        from src.agent_manager import create_agent

        result = create_agent(agent_cfg, global_cfg)

        mock_client.create_data_agent_sync.assert_called_once()
        assert result.name.endswith("test_agent")

    @patch("src.agent_manager._get_agent_client")
    def test_list_agents(self, mock_client_fn, global_cfg):
        mock_client = MagicMock()
        mock_client.list_data_agents.return_value = [
            MagicMock(name="projects/p/locations/global/dataAgents/a1"),
            MagicMock(name="projects/p/locations/global/dataAgents/a2"),
        ]
        mock_client_fn.return_value = mock_client

        from src.agent_manager import list_agents

        result = list_agents("test-project", "global")
        assert len(result) == 2

    @patch("src.agent_manager._get_agent_client")
    def test_delete_agent(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client

        from src.agent_manager import delete_agent

        delete_agent("test_agent", "test-project", "global")
        mock_client.delete_data_agent_sync.assert_called_once()

    @patch("src.agent_manager._get_agent_client")
    @patch("src.agent_manager._resolve_system_instruction")
    @patch("src.agent_manager._resolve_metadata")
    def test_update_agent(
        self, mock_meta, mock_instr, mock_client_fn, agent_cfg, global_cfg
    ):
        mock_instr.return_value = "Updated instruction."
        mock_meta.return_value = None

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.name = (
            "projects/test-project/locations/global/dataAgents/test_agent"
        )
        mock_client.update_data_agent_sync.return_value = mock_response
        mock_client_fn.return_value = mock_client

        from src.agent_manager import update_agent

        result = update_agent(agent_cfg, global_cfg)
        mock_client.update_data_agent_sync.assert_called_once()
        assert result.name.endswith("test_agent")
