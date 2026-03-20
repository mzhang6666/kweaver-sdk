"""E2E: Agent CRUD lifecycle — create → get → update → publish → unpublish → delete.

All tests are destructive and ordered. They share state via module-scoped fixtures.
Auto-discovers an available LLM model from the model-factory service.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from kweaver import KWeaverClient

pytestmark = [pytest.mark.e2e, pytest.mark.destructive]

TEST_PREFIX = f"sdk_e2e_{int(time.time())}"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def llm_model(kweaver_client: KWeaverClient) -> dict[str, str]:
    """Discover the first available LLM model from model-factory."""
    http = kweaver_client._http  # noqa: SLF001
    try:
        data = http.get("/api/mf-model-manager/v1/llm/list", params={"page": 1, "size": 100})
    except Exception:
        pytest.skip("model-factory not available")
    models = (data or {}).get("data", [])
    llm = next((m for m in models if m.get("model_type") == "llm"), None)
    if not llm:
        pytest.skip("no LLM model available in model-factory")
    return {"model_id": llm["model_id"], "model_name": llm["model_name"]}


@pytest.fixture(scope="module")
def created_agent(kweaver_client: KWeaverClient, llm_model: dict[str, str]) -> dict[str, Any]:
    """Create an agent for the test module; delete it at teardown."""
    config: dict[str, Any] = {
        "input": {"fields": [{"name": "user_input", "type": "string", "desc": ""}]},
        "output": {},
        "system_prompt": "你是一个 SDK 集成测试助手",
        "llms": [{
            "is_default": True,
            "llm_config": {
                "id": llm_model["model_id"],
                "name": llm_model["model_name"],
                "model_type": "llm",
                "max_tokens": 4096,
            },
        }],
    }

    result = kweaver_client.agents.create(
        name=f"{TEST_PREFIX}_agent",
        profile="E2E test agent — will be deleted",
        key=f"{TEST_PREFIX}_key",
        config=config,
    )
    assert result["id"], "create should return agent id"

    yield result

    # Cleanup: try unpublish + delete (ignore errors)
    try:
        kweaver_client.agents.unpublish(result["id"])
    except Exception:
        pass
    try:
        kweaver_client.agents.delete(result["id"])
    except Exception:
        pass


# ── Tests (ordered by lifecycle) ──────────────────────────────────────────────


class TestAgentCRUD:
    """Ordered agent CRUD lifecycle tests."""

    def test_create_returns_id(self, created_agent: dict[str, Any]):
        assert created_agent["id"]
        assert created_agent.get("version") is not None

    def test_get_by_id(self, kweaver_client: KWeaverClient, created_agent: dict[str, Any]):
        agent = kweaver_client.agents.get(created_agent["id"])
        assert agent.id == created_agent["id"]
        assert TEST_PREFIX in agent.name

    def test_get_by_key(self, kweaver_client: KWeaverClient):
        agent = kweaver_client.agents.get_by_key(f"{TEST_PREFIX}_key")
        assert agent.name
        assert TEST_PREFIX in agent.name

    def test_update(self, kweaver_client: KWeaverClient, created_agent: dict[str, Any]):
        # Fetch current state, modify, then update
        current = kweaver_client.agents.get(created_agent["id"])
        current_raw = kweaver_client._http.get(  # noqa: SLF001
            f"/api/agent-factory/v3/agent/{created_agent['id']}"
        )

        new_name = f"{TEST_PREFIX}_updated"
        current_raw["name"] = new_name
        kweaver_client.agents.update(created_agent["id"], {
            "name": new_name,
            "profile": current_raw.get("profile", ""),
            "avatar_type": current_raw.get("avatar_type", 1),
            "avatar": current_raw.get("avatar", "icon-dip-agent-default"),
            "product_key": current_raw.get("product_key", "DIP"),
            "config": current_raw.get("config", {}),
        })

        updated = kweaver_client.agents.get(created_agent["id"])
        assert updated.name == new_name

    # Known backend bug: publish crashes with nil pointer in umhttpaccess/names.go:32
    # when UM service returns (nil, nil). See: FillPublishedByName → GetUserIDNameMap → GetOsnNames
    # TODO: re-enable after decision-agent fixes nil check in names.go
    @pytest.mark.xfail(reason="backend bug: nil pointer in FillPublishedByName", strict=False)
    def test_publish(self, kweaver_client: KWeaverClient, created_agent: dict[str, Any]):
        result = kweaver_client.agents.publish(created_agent["id"])
        assert result.get("version") or result.get("release_id")

    @pytest.mark.xfail(reason="depends on publish (backend bug)", strict=False)
    def test_published_in_list(self, kweaver_client: KWeaverClient, created_agent: dict[str, Any]):
        agents = kweaver_client.agents.list(limit=100)
        found = any(a.id == created_agent["id"] for a in agents)
        assert found, "published agent should appear in list"

    @pytest.mark.xfail(reason="depends on publish (backend bug)", strict=False)
    def test_unpublish(self, kweaver_client: KWeaverClient, created_agent: dict[str, Any]):
        kweaver_client.agents.unpublish(created_agent["id"])
        # After unpublish, should not appear in published list
        agents = kweaver_client.agents.list(limit=100)
        found = any(a.id == created_agent["id"] for a in agents)
        assert not found, "unpublished agent should not appear in published list"

    def test_delete(self, kweaver_client: KWeaverClient, created_agent: dict[str, Any]):
        kweaver_client.agents.delete(created_agent["id"])
        with pytest.raises(Exception):
            kweaver_client.agents.get(created_agent["id"])
