"""SDK resource: conversations (decision-agent service)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

from kweaver.types import Conversation, Message, MessageChunk, Reference

if TYPE_CHECKING:
    from kweaver._http import HttpClient


class ConversationsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(
        self, agent_id: str, *, title: str | None = None
    ) -> Conversation:
        body: dict[str, Any] = {"agent_id": agent_id}
        if title:
            body["title"] = title
        data = self._http.post(
            "/api/decision-agent/v1/conversations", json=body
        )
        return _parse_conversation(data)

    def list(
        self, *, agent_id: str | None = None, limit: int | None = None
    ) -> list[Conversation]:
        params: dict[str, Any] = {}
        if agent_id:
            params["agent_id"] = agent_id
        if limit is not None:
            params["limit"] = limit
        data = self._http.get(
            "/api/decision-agent/v1/conversations", params=params or None
        )
        items = (
            data
            if isinstance(data, list)
            else (data.get("entries") or data.get("data") or [])
        )
        return [_parse_conversation(d) for d in items]

    def get(self, id: str) -> Conversation:
        data = self._http.get(f"/api/decision-agent/v1/conversations/{id}")
        return _parse_conversation(data)

    def send_message(
        self,
        conversation_id: str,
        content: str,
        *,
        stream: bool = False,
    ) -> Message | Iterator[MessageChunk]:
        body: dict[str, Any] = {"content": content, "stream": stream}
        path = f"/api/decision-agent/v1/conversations/{conversation_id}/messages"

        if not stream:
            data = self._http.post(path, json=body)
            return _parse_message(data)

        return self._stream_message(path, body)

    def _stream_message(
        self, path: str, body: dict[str, Any]
    ) -> Iterator[MessageChunk]:
        for event in self._http.stream_post(path, json=body):
            refs = [Reference(**r) for r in event.get("references", [])]
            yield MessageChunk(
                delta=event.get("delta", ""),
                finished=event.get("finished", False),
                references=refs,
            )

    def list_messages(
        self,
        conversation_id: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Message]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = self._http.get(
            f"/api/decision-agent/v1/conversations/{conversation_id}/messages",
            params=params or None,
        )
        items = (
            data
            if isinstance(data, list)
            else (data.get("entries") or data.get("data") or [])
        )
        return [_parse_message(d) for d in items]

    def delete(self, id: str) -> None:
        self._http.delete(f"/api/decision-agent/v1/conversations/{id}")


def _parse_conversation(d: Any) -> Conversation:
    return Conversation(
        id=str(d.get("id", "")),
        agent_id=d.get("agent_id", ""),
        title=d.get("title"),
        message_count=d.get("message_count", 0),
        last_active=d.get("last_active"),
    )


def _parse_message(d: Any) -> Message:
    refs = [Reference(**r) for r in d.get("references", [])]
    return Message(
        id=str(d.get("id", "")),
        role=d.get("role", ""),
        content=d.get("content", ""),
        references=refs,
        timestamp=d.get("timestamp", ""),
    )
