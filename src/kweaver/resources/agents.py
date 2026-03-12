"""SDK resource: agents (decision-agent service)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kweaver.types import Agent

if TYPE_CHECKING:
    from kweaver._http import HttpClient


class AgentsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self, *, keyword: str | None = None, status: str | None = None
    ) -> list[Agent]:
        params: dict[str, Any] = {}
        if keyword:
            params["keyword"] = keyword
        if status:
            params["status"] = status
        data = self._http.get(
            "/api/decision-agent/v1/agents", params=params or None
        )
        items = (
            data
            if isinstance(data, list)
            else (data.get("entries") or data.get("data") or [])
        )
        return [_parse_agent(d) for d in items]

    def get(self, id: str) -> Agent:
        data = self._http.get(f"/api/decision-agent/v1/agents/{id}")
        return _parse_agent(data)


def _parse_agent(d: Any) -> Agent:
    return Agent(
        id=str(d.get("id", "")),
        name=d.get("name", ""),
        description=d.get("description"),
        status=d.get("status", "draft"),
        kn_ids=d.get("kn_ids", []),
        system_prompt=d.get("system_prompt"),
        capabilities=d.get("capabilities", []),
        model_config_data=d.get("model_config"),
        conversation_count=d.get("conversation_count", 0),
    )
