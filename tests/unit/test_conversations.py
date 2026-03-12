"""Tests for conversations resource."""

from unittest.mock import patch

import httpx

from tests.conftest import RequestCapture, make_client


def test_create_conversation(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "id": "conv_01", "agent_id": "agent_01", "title": "测试会话",
        })

    client = make_client(handler, capture)
    conv = client.conversations.create("agent_01", title="测试会话")
    assert conv.id == "conv_01"
    assert conv.agent_id == "agent_01"
    body = capture.last_body()
    assert body["agent_id"] == "agent_01"
    assert body["title"] == "测试会话"


def test_list_conversations(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [
            {"id": "conv_01", "agent_id": "a1", "title": "会话1", "message_count": 5,
             "last_active": "2026-03-12T10:00:00Z"},
            {"id": "conv_02", "agent_id": "a1", "title": "会话2", "message_count": 3},
        ]})

    client = make_client(handler, capture)
    convs = client.conversations.list(agent_id="a1", limit=10)
    assert len(convs) == 2
    assert convs[0].message_count == 5
    assert convs[0].last_active == "2026-03-12T10:00:00Z"
    url = capture.last_url()
    assert "agent_id=a1" in url


def test_get_conversation():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "id": "conv_01", "agent_id": "a1", "message_count": 3,
        })

    client = make_client(handler)
    conv = client.conversations.get("conv_01")
    assert conv.id == "conv_01"


def test_send_message_sync(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "id": "msg_02", "role": "assistant",
            "content": "物料库存充足",
            "references": [
                {"source": "库存表", "content": "华东仓 1200件", "score": 0.95},
            ],
            "timestamp": "2026-03-12T10:01:00Z",
        })

    client = make_client(handler, capture)
    reply = client.conversations.send_message("conv_01", "库存情况？")
    assert reply.role == "assistant"
    assert reply.content == "物料库存充足"
    assert len(reply.references) == 1
    assert reply.references[0].source == "库存表"
    assert reply.references[0].score == 0.95
    body = capture.last_body()
    assert body["content"] == "库存情况？"
    assert body["stream"] is False


def test_send_message_stream():
    chunks = [
        {"delta": "物料", "finished": False, "references": []},
        {"delta": "库存充足", "finished": True,
         "references": [{"source": "库存表", "content": "1200件", "score": 0.9}]},
    ]
    client = make_client(lambda r: httpx.Response(200, json={}))
    with patch.object(
        client.conversations._http, "stream_post", return_value=iter(chunks)
    ):
        result = list(
            client.conversations.send_message("conv_01", "hi", stream=True)
        )
    assert len(result) == 2
    assert result[0].delta == "物料"
    assert not result[0].finished
    assert result[1].delta == "库存充足"
    assert result[1].finished
    assert result[1].references[0].source == "库存表"


def test_list_messages(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [
            {"id": "m1", "role": "user", "content": "你好",
             "references": [], "timestamp": "2026-03-12T10:00:00Z"},
            {"id": "m2", "role": "assistant", "content": "你好！",
             "references": [], "timestamp": "2026-03-12T10:00:01Z"},
        ]})

    client = make_client(handler, capture)
    msgs = client.conversations.list_messages("conv_01", limit=20)
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[1].role == "assistant"
    assert "/conv_01/messages" in capture.last_url()


def test_delete_conversation(capture: RequestCapture):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    client = make_client(handler, capture)
    client.conversations.delete("conv_01")
    assert "/conversations/conv_01" in capture.last_url()
