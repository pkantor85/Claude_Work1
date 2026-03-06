"""
Tests for src/conversation_manager.py

Mocks the CA API clients to test conversation lifecycle logic.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestConversationManager:
    @patch("src.conversation_manager._get_chat_client")
    def test_create_conversation(self, mock_client_fn):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.name = (
            "projects/p/locations/global/conversations/conv_123"
        )
        mock_client.create_conversation.return_value = mock_response
        mock_client_fn.return_value = mock_client

        from src.conversation_manager import create_conversation

        result = create_conversation(
            agent_id="agent_1",
            project_id="p",
            location="global",
            conversation_id="conv_123",
        )
        mock_client.create_conversation.assert_called_once()
        assert "conv_123" in result.name

    @patch("src.conversation_manager._get_chat_client")
    def test_list_conversations(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.list_conversations.return_value = [
            MagicMock(name="projects/p/locations/global/conversations/c1"),
            MagicMock(name="projects/p/locations/global/conversations/c2"),
        ]
        mock_client_fn.return_value = mock_client

        from src.conversation_manager import list_conversations

        result = list_conversations("p", "global")
        assert len(result) == 2

    @patch("src.conversation_manager._get_chat_client")
    def test_delete_conversation(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client_fn.return_value = mock_client

        from src.conversation_manager import delete_conversation

        delete_conversation("conv_1", "p", "global")
        mock_client.delete_conversation.assert_called_once()

    @patch("src.conversation_manager._get_chat_client")
    def test_send_message_stateful(self, mock_client_fn):
        """Test that send_message_stateful streams and parses responses."""
        mock_client = MagicMock()

        # Simulate a stream with one text response
        mock_msg = MagicMock()
        mock_msg.system_message = MagicMock()
        # Simulate text field
        mock_text = MagicMock()
        mock_text.parts = ["Hello, world!"]
        mock_text.text_type = "FINAL_RESPONSE"

        # Make "text" in system_message return True
        mock_msg.system_message.__contains__ = lambda self, x: x == "text"
        mock_msg.system_message.text = mock_text

        mock_client.chat.return_value = iter([mock_msg])
        mock_client_fn.return_value = mock_client

        from src.conversation_manager import send_message_stateful

        responses = send_message_stateful(
            question="What is the total?",
            agent_id="agent_1",
            conversation_id="conv_1",
            project_id="p",
            location="global",
        )
        assert len(responses) == 1
        mock_client.chat.assert_called_once()

    @patch("src.conversation_manager._get_chat_client")
    def test_list_messages(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.list_messages.return_value = [
            MagicMock(), MagicMock()
        ]
        mock_client_fn.return_value = mock_client

        from src.conversation_manager import list_messages

        result = list_messages("conv_1", "p", "global")
        assert len(result) == 2
