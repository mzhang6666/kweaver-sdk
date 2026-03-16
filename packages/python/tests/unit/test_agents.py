"""Tests for agents resource (agent-factory v3 API)."""

import httpx

from tests.conftest import RequestCapture, make_client


def _agent_list_json(**overrides):
    """Simulates agent-factory /personal-space/agent-list response item."""
    base = {
        "id": "agent_01",
        "key": "key_01",
        "name": "供应链助手",
        "profile": "供应链领域问答",
        "version": "v5",
        "status": "published",
        "is_built_in": 0,
    }
    base.update(overrides)
    return base


def _agent_detail_json(**overrides):
    """Simulates agent-factory /agent/{id} response."""
    base = {
        "id": "agent_01",
        "key": "key_01",
        "name": "供应链助手",
        "profile": "供应链领域问答",
        "version": "v5",
        "status": "published",
        "config": {
            "system_prompt": "你是供应链专家",
            "data_source": {
                "kg": [{"kg_id": "kn_01", "fields": []}],
            },
            "llms": [{"is_default": True, "llm_config": {"name": "deepseek_v3"}}],
        },
    }
    base.update(overrides)
    return base


def test_list_agents():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entries": [_agent_list_json()]})

    client = make_client(handler)
    agents = client.agents.list()
    assert len(agents) == 1
    assert agents[0].id == "agent_01"
    assert agents[0].name == "供应链助手"
    assert agents[0].status == "published"


def test_list_agents_with_filters(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entries": []})

    client = make_client(handler, capture)
    client.agents.list(keyword="供应链", status="published")
    url = capture.last_url()
    assert "name=" in url
    assert "publish_status=published" in url


def test_list_agents_with_offset_limit(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entries": []})

    client = make_client(handler, capture)
    client.agents.list(offset=10, limit=20)
    url = capture.last_url()
    assert "offset=10" in url
    assert "limit=20" in url


def test_list_agents_raw_list():
    """API returning a plain list (instead of {entries: [...]})."""
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[_agent_list_json()])

    client = make_client(handler)
    agents = client.agents.list()
    assert len(agents) == 1


def test_get_agent(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_agent_detail_json())

    client = make_client(handler, capture)
    agent = client.agents.get("agent_01")
    assert agent.id == "agent_01"
    assert agent.key == "key_01"
    assert agent.version == "v5"
    assert agent.system_prompt == "你是供应链专家"
    assert agent.kn_ids == ["kn_01"]
    assert "/agent/agent_01" in capture.last_url()


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


def test_status_mapping():
    """published_edited should map to published."""
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entries": [
            _agent_list_json(status="published_edited"),
        ]})

    client = make_client(handler)
    agents = client.agents.list()
    assert agents[0].status == "published"
