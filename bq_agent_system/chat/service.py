"""Chat service for interacting with CA API data agents."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Generator

from google.cloud import geminidataanalytics

logger = logging.getLogger(__name__)


@dataclass
class ChatResponseChunk:
    """A single parsed chunk from the streaming chat response.

    Attributes:
        kind: One of ``thought``, ``progress``, ``answer``, ``error``,
            ``query``, ``data``, ``chart``, ``text``.
        content: The raw string or dict payload.
    """

    kind: str
    content: Any


class ChatService:
    """Manages conversations and chat with CA API agents."""

    def __init__(self, project_id: str, location: str = "global"):
        self.project_id = project_id
        self.location = location
        self.client = geminidataanalytics.DataChatServiceClient()
        self._parent = f"projects/{project_id}/locations/{location}"

    def create_conversation(self, agent_name: str, conversation_id: str | None = None) -> str:
        """Create a new stateful conversation linked to an agent.

        Args:
            agent_name: Full resource name of the data agent.
            conversation_id: Optional custom ID; auto-generated if omitted.

        Returns:
            The full resource name of the created conversation.
        """
        conv = geminidataanalytics.Conversation()
        conv.agents = [agent_name]

        conv_id = conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
        request = geminidataanalytics.CreateConversationRequest(
            parent=self._parent,
            conversation_id=conv_id,
            conversation=conv,
        )
        response = self.client.create_conversation(request=request)
        logger.info("Created conversation: %s", response.name)
        return response.name

    def send_message(
        self,
        conversation_name: str,
        agent_name: str,
        question: str,
    ) -> Generator[ChatResponseChunk, None, None]:
        """Send a question and yield streaming response chunks.

        Args:
            conversation_name: Full resource name of the conversation.
            agent_name: Full resource name of the data agent.
            question: Natural language question.

        Yields:
            ChatResponseChunk objects for each part of the response.
        """
        user_msg = geminidataanalytics.UserMessage(text=question)
        conv_ref = geminidataanalytics.ConversationReference()
        conv_ref.conversation = conversation_name
        conv_ref.data_agent = agent_name

        request = geminidataanalytics.ChatRequest(
            parent=self._parent,
            messages=[user_msg],
            conversation_reference=conv_ref,
        )

        for resp in self.client.chat(request=request):
            yield from self._parse_response(resp)

    @staticmethod
    def _parse_response(resp: Any) -> Generator[ChatResponseChunk, None, None]:
        """Parse a single streaming response into typed chunks."""
        if hasattr(resp, "system_message") and resp.system_message:
            msg = resp.system_message
            text = getattr(msg, "text", None)
            text_type = getattr(msg, "text_type", None)

            if text_type and str(text_type).upper() == "THOUGHT":
                yield ChatResponseChunk(kind="thought", content=text or "")
            elif text_type and str(text_type).upper() == "PROGRESS":
                yield ChatResponseChunk(kind="progress", content=text or "")
            elif text_type and str(text_type).upper() == "ERROR":
                yield ChatResponseChunk(kind="error", content=text or "")
            elif text:
                yield ChatResponseChunk(kind="answer", content=text)

        if hasattr(resp, "message") and resp.message:
            msg = resp.message
            content = getattr(msg, "content", "")
            msg_type = getattr(msg, "type", "")

            type_str = str(msg_type).lower() if msg_type else ""
            if "query" in type_str or "sql" in type_str:
                yield ChatResponseChunk(kind="query", content=content)
            elif "chart" in type_str or "vega" in type_str:
                yield ChatResponseChunk(kind="chart", content=content)
            elif "data" in type_str:
                yield ChatResponseChunk(kind="data", content=content)
            else:
                yield ChatResponseChunk(kind="text", content=content)


class ChatSession:
    """High-level wrapper managing a single conversation session.

    Tracks message history and provides a simple ``ask()`` interface
    suitable for driving a chat UI.
    """

    def __init__(self, chat_service: ChatService, agent_name: str):
        self.chat_service = chat_service
        self.agent_name = agent_name
        self.conversation_name: str | None = None
        self.history: list[dict[str, Any]] = []

    def start(self) -> str:
        """Start a new conversation. Returns the conversation resource name."""
        self.conversation_name = self.chat_service.create_conversation(self.agent_name)
        self.history = []
        return self.conversation_name

    def ask(self, question: str) -> Generator[ChatResponseChunk, None, None]:
        """Send a question and yield response chunks.

        Automatically starts a conversation if one hasn't been created yet.
        Records messages in history.
        """
        if not self.conversation_name:
            self.start()

        self.history.append({"role": "user", "content": question})

        answer_parts: list[str] = []
        for chunk in self.chat_service.send_message(
            self.conversation_name, self.agent_name, question
        ):
            if chunk.kind in ("answer", "text"):
                answer_parts.append(str(chunk.content))
            yield chunk

        if answer_parts:
            self.history.append({"role": "assistant", "content": "\n".join(answer_parts)})
