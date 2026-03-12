"""Skill: chat_agent — interact with a Decision Agent."""

from __future__ import annotations

from typing import Any

from kweaver.skills._base import BaseSkill


class ChatAgentSkill(BaseSkill):
    def _execute(self, **kwargs: Any) -> dict[str, Any]:
        mode: str = kwargs["mode"]

        if mode == "ask":
            return self._ask(kwargs)
        elif mode == "history":
            return self._history(kwargs)
        elif mode == "sessions":
            return self._sessions(kwargs)
        else:
            return {"error": True, "message": f"未知模式: {mode}"}

    def _ask(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        agent_id = self._resolve_agent_id(kwargs)
        if agent_id is None:
            return {"error": True, "message": "未找到指定的 Agent"}

        question: str = kwargs.get("question", "")
        conversation_id = kwargs.get("conversation_id")
        stream = kwargs.get("stream", False)

        if not conversation_id:
            conv = self.client.conversations.create(agent_id)
            conversation_id = conv.id

        if stream:
            chunks = []
            references = []
            for chunk in self.client.conversations.send_message(
                conversation_id, question, stream=True
            ):
                chunks.append(chunk.delta)
                if chunk.references:
                    references = chunk.references
            answer = "".join(chunks)
            refs = [
                {"source": r.source, "content": r.content, "score": r.score}
                for r in references
            ]
        else:
            reply = self.client.conversations.send_message(
                conversation_id, question
            )
            answer = reply.content
            refs = [
                {"source": r.source, "content": r.content, "score": r.score}
                for r in reply.references
            ]

        return {
            "answer": answer,
            "conversation_id": conversation_id,
            "references": refs,
        }

    def _history(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        conversation_id = kwargs.get("conversation_id")
        if not conversation_id:
            return {"error": True, "message": "conversation_id 是必填参数"}

        limit = kwargs.get("limit", 50)
        messages = self.client.conversations.list_messages(
            conversation_id, limit=limit
        )
        return {
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                }
                for m in messages
            ]
        }

    def _sessions(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        agent_id = self._resolve_agent_id(kwargs)
        if agent_id is None:
            return {"error": True, "message": "未找到指定的 Agent"}

        conversations = self.client.conversations.list(agent_id=agent_id)
        return {
            "conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "message_count": c.message_count,
                    "last_active": c.last_active,
                }
                for c in conversations
            ]
        }

    def _resolve_agent_id(self, kwargs: dict[str, Any]) -> str | None:
        agent_id = kwargs.get("agent_id")
        if agent_id:
            return agent_id
        agent_name = kwargs.get("agent_name")
        if agent_name:
            agents = self.client.agents.list(keyword=agent_name)
            if agents:
                return agents[0].id
        return None
