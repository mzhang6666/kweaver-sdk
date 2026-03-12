"""Tests for agents resource."""

import httpx

from tests.conftest import RequestCapture, make_client


def _agent_json(**overrides):
    base = {
        "id": "agent_01",
        "name": "供应链助手",
        "description": "供应链领域问答",
        "status": "published",
        "kn_ids": ["kn_01"],
        "system_prompt": "你是供应链专家",
        "capabilities": ["知识问答", "数据查询"],
        "model_config": {"temperature": 0.7},
        "conversation_count": 10,
    }
    base.update(overrides)
    return base


def test_list_agents():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [_agent_json()]})

    client = make_client(handler)
    agents = client.agents.list()
    assert len(agents) == 1
    assert agents[0].id == "agent_01"
    assert agents[0].name == "供应链助手"
    assert agents[0].status == "published"
    assert agents[0].kn_ids == ["kn_01"]
    assert agents[0].capabilities == ["知识问答", "数据查询"]


def test_list_agents_with_filters(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    client = make_client(handler, capture)
    client.agents.list(keyword="供应链", status="published")
    url = capture.last_url()
    assert "keyword=" in url
    assert "status=published" in url


def test_list_agents_raw_list():
    """API returning a plain list (instead of {data: [...]})."""
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_agent_json()])

    client = make_client(handler)
    agents = client.agents.list()
    assert len(agents) == 1


def test_get_agent(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_agent_json())

    client = make_client(handler, capture)
    agent = client.agents.get("agent_01")
    assert agent.id == "agent_01"
    assert agent.system_prompt == "你是供应链专家"
    assert agent.model_config_data == {"temperature": 0.7}
    assert agent.conversation_count == 10
    assert "/agents/agent_01" in capture.last_url()


def test_get_agent_minimal_fields():
    """Agent with only required fields."""
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "a1", "name": "test"})

    client = make_client(handler)
    agent = client.agents.get("a1")
    assert agent.id == "a1"
    assert agent.status == "draft"
    assert agent.kn_ids == []
    assert agent.capabilities == []
    assert agent.conversation_count == 0
