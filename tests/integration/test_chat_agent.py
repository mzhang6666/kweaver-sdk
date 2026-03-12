"""Tests for chat_agent skill."""

from unittest.mock import MagicMock

from kweaver.skills.chat_agent import ChatAgentSkill
from kweaver.types import (
    Agent,
    Conversation,
    Message,
    MessageChunk,
    Reference,
)


def _make_agent(**overrides):
    defaults = {"id": "agent_01", "name": "供应链助手", "status": "published"}
    defaults.update(overrides)
    return Agent(**defaults)


def test_ask_mode_creates_conversation():
    mock_client = MagicMock()
    mock_client.conversations.create.return_value = Conversation(
        id="conv_new", agent_id="agent_01",
    )
    mock_client.conversations.send_message.return_value = Message(
        id="m1", role="assistant", content="库存充足",
        references=[Reference(source="库存表", content="1200件", score=0.9)],
        timestamp="2026-03-12T10:00:00Z",
    )

    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(mode="ask", agent_id="agent_01", question="库存情况？")

    assert result["answer"] == "库存充足"
    assert result["conversation_id"] == "conv_new"
    assert len(result["references"]) == 1
    assert result["references"][0]["source"] == "库存表"
    mock_client.conversations.create.assert_called_once_with("agent_01")


def test_ask_mode_reuses_conversation():
    mock_client = MagicMock()
    mock_client.conversations.send_message.return_value = Message(
        id="m2", role="assistant", content="继续回复",
        timestamp="2026-03-12T10:01:00Z",
    )

    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(
        mode="ask", agent_id="agent_01",
        question="继续", conversation_id="conv_exist",
    )

    assert result["conversation_id"] == "conv_exist"
    mock_client.conversations.create.assert_not_called()


def test_ask_mode_stream():
    mock_client = MagicMock()
    mock_client.conversations.create.return_value = Conversation(
        id="conv_s", agent_id="agent_01",
    )
    mock_client.conversations.send_message.return_value = iter([
        MessageChunk(delta="物料", finished=False),
        MessageChunk(
            delta="库存充足", finished=True,
            references=[Reference(source="库存表", content="1200", score=0.9)],
        ),
    ])

    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(
        mode="ask", agent_id="agent_01", question="库存？", stream=True,
    )

    assert result["answer"] == "物料库存充足"
    assert result["references"][0]["source"] == "库存表"


def test_ask_mode_resolve_by_name():
    mock_client = MagicMock()
    mock_client.agents.list.return_value = [_make_agent()]
    mock_client.conversations.create.return_value = Conversation(
        id="conv_01", agent_id="agent_01",
    )
    mock_client.conversations.send_message.return_value = Message(
        id="m1", role="assistant", content="OK",
        timestamp="2026-03-12T10:00:00Z",
    )

    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(mode="ask", agent_name="供应链助手", question="hi")

    assert result["answer"] == "OK"
    mock_client.agents.list.assert_called_once_with(keyword="供应链助手")


def test_ask_mode_agent_not_found():
    mock_client = MagicMock()
    mock_client.agents.list.return_value = []

    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(mode="ask", agent_name="不存在", question="hi")

    assert result["error"] is True
    assert "未找到" in result["message"]


def test_history_mode():
    mock_client = MagicMock()
    mock_client.conversations.list_messages.return_value = [
        Message(id="m1", role="user", content="你好",
                timestamp="2026-03-12T10:00:00Z"),
        Message(id="m2", role="assistant", content="你好！",
                timestamp="2026-03-12T10:00:01Z"),
    ]

    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(mode="history", conversation_id="conv_01", limit=20)

    assert len(result["messages"]) == 2
    assert result["messages"][0]["role"] == "user"
    mock_client.conversations.list_messages.assert_called_once_with(
        "conv_01", limit=20,
    )


def test_history_mode_missing_id():
    mock_client = MagicMock()
    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(mode="history")

    assert result["error"] is True
    assert "conversation_id" in result["message"]


def test_sessions_mode():
    mock_client = MagicMock()
    mock_client.conversations.list.return_value = [
        Conversation(id="c1", agent_id="a1", title="会话1", message_count=5,
                     last_active="2026-03-12T10:00:00Z"),
        Conversation(id="c2", agent_id="a1", title="会话2", message_count=3),
    ]

    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(mode="sessions", agent_id="a1")

    assert len(result["conversations"]) == 2
    assert result["conversations"][0]["title"] == "会话1"
    mock_client.conversations.list.assert_called_once_with(agent_id="a1")


def test_unknown_mode():
    mock_client = MagicMock()
    skill = ChatAgentSkill(client=mock_client)
    result = skill.run(mode="unknown")
    assert result["error"] is True
