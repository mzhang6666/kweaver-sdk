"""Tests for discover_agents skill."""

from unittest.mock import MagicMock

from kweaver.skills.discover_agents import DiscoverAgentsSkill
from kweaver.types import Agent, KnowledgeNetwork


def _make_agent(**overrides):
    defaults = {
        "id": "agent_01", "name": "供应链助手",
        "description": "供应链领域问答", "status": "published",
        "kn_ids": ["kn_01"], "system_prompt": "你是供应链专家",
        "capabilities": ["知识问答", "数据查询"],
        "conversation_count": 10,
    }
    defaults.update(overrides)
    return Agent(**defaults)


def test_list_mode():
    mock_client = MagicMock()
    mock_client.agents.list.return_value = [
        _make_agent(),
        _make_agent(id="agent_02", name="HR 问答", kn_ids=["kn_02"]),
    ]
    mock_client.knowledge_networks.get.side_effect = lambda kn_id: (
        KnowledgeNetwork(id=kn_id, name=f"KN_{kn_id}")
    )

    skill = DiscoverAgentsSkill(client=mock_client)
    result = skill.run(mode="list")

    assert len(result["agents"]) == 2
    assert result["agents"][0]["name"] == "供应链助手"
    assert result["agents"][0]["knowledge_networks"] == ["KN_kn_01"]
    assert result["agents"][1]["knowledge_networks"] == ["KN_kn_02"]


def test_list_mode_with_keyword():
    mock_client = MagicMock()
    mock_client.agents.list.return_value = []

    skill = DiscoverAgentsSkill(client=mock_client)
    result = skill.run(mode="list", keyword="供应链", status="published")

    assert result == {"agents": []}
    mock_client.agents.list.assert_called_once_with(
        keyword="供应链", status="published"
    )


def test_detail_mode():
    mock_client = MagicMock()
    mock_client.agents.get.return_value = _make_agent(
        system_prompt="你是一个供应链领域的专家助手" * 20,
    )
    mock_client.knowledge_networks.get.return_value = KnowledgeNetwork(
        id="kn_01", name="供应链知识网络",
    )

    skill = DiscoverAgentsSkill(client=mock_client)
    result = skill.run(mode="detail", agent_id="agent_01")

    agent = result["agent"]
    assert agent["id"] == "agent_01"
    assert agent["capabilities"] == ["知识问答", "数据查询"]
    assert agent["knowledge_networks"] == [{"id": "kn_01", "name": "供应链知识网络"}]
    # Prompt should be truncated to 200 chars
    assert len(agent["prompts"]["system_prompt_preview"]) == 200
    assert agent["conversation_count"] == 10


def test_detail_mode_resolve_by_name():
    mock_client = MagicMock()
    mock_client.agents.list.return_value = [_make_agent()]
    mock_client.agents.get.return_value = _make_agent()
    mock_client.knowledge_networks.get.return_value = KnowledgeNetwork(
        id="kn_01", name="KN",
    )

    skill = DiscoverAgentsSkill(client=mock_client)
    result = skill.run(mode="detail", agent_name="供应链助手")

    assert "agent" in result
    mock_client.agents.list.assert_called_once_with(keyword="供应链助手")


def test_detail_mode_agent_not_found():
    mock_client = MagicMock()
    mock_client.agents.list.return_value = []

    skill = DiscoverAgentsSkill(client=mock_client)
    result = skill.run(mode="detail", agent_name="不存在")

    assert result["error"] is True
    assert "未找到" in result["message"]


def test_detail_mode_no_prompt():
    mock_client = MagicMock()
    mock_client.agents.get.return_value = _make_agent(system_prompt=None)
    mock_client.knowledge_networks.get.return_value = KnowledgeNetwork(
        id="kn_01", name="KN",
    )

    skill = DiscoverAgentsSkill(client=mock_client)
    result = skill.run(mode="detail", agent_id="agent_01")

    assert result["agent"]["prompts"]["system_prompt_preview"] is None


def test_unknown_mode():
    mock_client = MagicMock()
    skill = DiscoverAgentsSkill(client=mock_client)
    result = skill.run(mode="unknown")
    assert result["error"] is True
