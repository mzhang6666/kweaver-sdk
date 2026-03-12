"""E2E: agent listing and conversation.

Read-only tests for agent listing. Conversation tests marked destructive.
"""

from __future__ import annotations

import pytest

from kweaver import ADPClient

pytestmark = pytest.mark.e2e


def test_list_agents(adp_client: ADPClient):
    """List agents should return without error."""
    agents = adp_client.agents.list()
    assert isinstance(agents, list)


def test_list_agents_published(adp_client: ADPClient):
    """Published filter should only return published agents."""
    agents = adp_client.agents.list(status="published")
    assert isinstance(agents, list)
    for a in agents:
        assert a.status == "published"


@pytest.fixture(scope="module")
def published_agent(adp_client: ADPClient):
    """Find a published agent for tests."""
    agents = adp_client.agents.list(status="published")
    if not agents:
        pytest.skip("No published agents found")
    return agents[0]


def test_get_agent(adp_client: ADPClient, published_agent):
    """Get agent detail should match list result."""
    agent = adp_client.agents.get(published_agent.id)
    assert agent.id == published_agent.id
    assert agent.name == published_agent.name


@pytest.mark.destructive
def test_conversation_flow(adp_client: ADPClient, published_agent):
    """Create conversation, send message, list messages, delete."""
    conv = adp_client.conversations.create(published_agent.id)
    assert conv.id
    assert conv.agent_id == published_agent.id

    try:
        reply = adp_client.conversations.send_message(conv.id, content="你好")
        assert reply.content
        assert reply.role == "assistant"

        messages = adp_client.conversations.list_messages(conv.id)
        assert len(messages) >= 2  # user + assistant
    finally:
        adp_client.conversations.delete(conv.id)
