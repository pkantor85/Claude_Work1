"""
conversation_manager — Conversation lifecycle & chat streaming.

Handles:
* Creating conversations linked to a Data Agent
* Sending stateful (or stateless) chat messages
* Streaming and collecting responses
* Listing / deleting conversations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional

from google.cloud import geminidataanalytics

from src.response_handler import AgentResponse, parse_stream_message
from src.utils import (
    agent_resource_name,
    conversation_resource_name,
    get_logger,
    parent_resource_name,
)

logger = get_logger(__name__)

# ── Client singleton ──────────────────────────────────────

_chat_client: Optional[geminidataanalytics.DataChatServiceClient] = None


def _get_chat_client() -> geminidataanalytics.DataChatServiceClient:
    global _chat_client
    if _chat_client is None:
        _chat_client = geminidataanalytics.DataChatServiceClient()
    return _chat_client


# ── Conversation CRUD ─────────────────────────────────────


def create_conversation(
    agent_id: str,
    project_id: str,
    location: str = "global",
    conversation_id: Optional[str] = None,
) -> geminidataanalytics.Conversation:
    """
    Create a new stateful conversation linked to a Data Agent.

    If *conversation_id* is not supplied the API will auto-generate one.
    """
    client = _get_chat_client()

    conversation = geminidataanalytics.Conversation()
    conversation.agents = [
        agent_resource_name(project_id, location, agent_id)
    ]

    kwargs: dict = {
        "parent": parent_resource_name(project_id, location),
        "conversation": conversation,
    }
    if conversation_id:
        kwargs["conversation_id"] = conversation_id
        conversation.name = conversation_resource_name(
            project_id, location, conversation_id
        )

    request = geminidataanalytics.CreateConversationRequest(**kwargs)
    response = client.create_conversation(request=request)
    logger.info("Conversation created: %s", response.name)
    return response


def list_conversations(
    project_id: str,
    location: str = "global",
) -> list[geminidataanalytics.Conversation]:
    """List all conversations in the project."""
    client = _get_chat_client()
    request = geminidataanalytics.ListConversationsRequest(
        parent=parent_resource_name(project_id, location),
    )
    return list(client.list_conversations(request=request))


def get_conversation(
    conversation_id: str,
    project_id: str,
    location: str = "global",
) -> geminidataanalytics.Conversation:
    """Retrieve a specific conversation."""
    client = _get_chat_client()
    request = geminidataanalytics.GetConversationRequest(
        name=conversation_resource_name(project_id, location, conversation_id)
    )
    return client.get_conversation(request=request)


def list_messages(
    conversation_id: str,
    project_id: str,
    location: str = "global",
) -> list:
    """List all messages in a conversation."""
    client = _get_chat_client()
    request = geminidataanalytics.ListMessagesRequest(
        parent=conversation_resource_name(
            project_id, location, conversation_id
        ),
    )
    return list(client.list_messages(request=request))


def delete_conversation(
    conversation_id: str,
    project_id: str,
    location: str = "global",
) -> None:
    """Delete a conversation."""
    client = _get_chat_client()
    request = geminidataanalytics.DeleteConversationRequest(
        name=conversation_resource_name(project_id, location, conversation_id)
    )
    client.delete_conversation(request=request)
    logger.info("Conversation deleted: %s", conversation_id)


# ── Chat (stateful) ──────────────────────────────────────


def send_message_stateful(
    question: str,
    agent_id: str,
    conversation_id: str,
    project_id: str,
    location: str = "global",
    timeout: int = 300,
    on_message: Optional[Callable[[AgentResponse], None]] = None,
) -> list[AgentResponse]:
    """
    Send a message in a stateful conversation and stream the response.

    Parameters
    ----------
    question:
        Natural language question.
    agent_id:
        The Data Agent to query.
    conversation_id:
        Existing conversation ID.
    project_id / location:
        GCP identifiers.
    timeout:
        Request timeout in seconds (max 600).
    on_message:
        Optional callback invoked for each streamed message chunk.

    Returns
    -------
    list[AgentResponse]
        All parsed response chunks.
    """
    client = _get_chat_client()

    messages = [geminidataanalytics.Message()]
    messages[0].user_message.text = question

    conversation_reference = geminidataanalytics.ConversationReference()
    conversation_reference.conversation = conversation_resource_name(
        project_id, location, conversation_id
    )
    conversation_reference.data_agent_context.data_agent = (
        agent_resource_name(project_id, location, agent_id)
    )

    request = geminidataanalytics.ChatRequest(
        parent=parent_resource_name(project_id, location),
        messages=messages,
        conversation_reference=conversation_reference,
    )

    logger.info(
        "Sending message to agent '%s' in conversation '%s'",
        agent_id,
        conversation_id,
    )

    responses: list[AgentResponse] = []
    stream = client.chat(request=request, timeout=timeout)

    for raw_msg in stream:
        parsed = parse_stream_message(raw_msg)
        responses.append(parsed)
        if on_message:
            on_message(parsed)

    return responses


# ── Chat (stateless) ─────────────────────────────────────


def send_message_stateless(
    question: str,
    agent_id: str,
    project_id: str,
    location: str = "global",
    conversation_history: Optional[list] = None,
    timeout: int = 300,
    on_message: Optional[Callable[[AgentResponse], None]] = None,
) -> list[AgentResponse]:
    """
    Send a stateless chat message (application manages history).

    Parameters
    ----------
    question:
        Natural language question.
    agent_id:
        The Data Agent to query.
    conversation_history:
        Previous messages for multi-turn context.
    """
    client = _get_chat_client()

    messages = list(conversation_history or [])
    new_msg = geminidataanalytics.Message()
    new_msg.user_message.text = question
    messages.append(new_msg)

    data_agent_context = geminidataanalytics.DataAgentContext()
    data_agent_context.data_agent = agent_resource_name(
        project_id, location, agent_id
    )

    request = geminidataanalytics.ChatRequest(
        parent=parent_resource_name(project_id, location),
        messages=messages,
        data_agent_context=data_agent_context,
    )

    responses: list[AgentResponse] = []
    stream = client.chat(request=request, timeout=timeout)

    for raw_msg in stream:
        parsed = parse_stream_message(raw_msg)
        responses.append(parsed)
        if on_message:
            on_message(parsed)

    return responses
