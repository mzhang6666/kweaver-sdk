"""SDK resource: agents (agent-factory service).

Actual backend endpoints (agent-factory v3):
  - List:   GET  /api/agent-factory/v3/personal-space/agent-list
  - Detail: GET  /api/agent-factory/v3/agent/{id}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kweaver.types import Agent

if TYPE_CHECKING:
    from kweaver._http import HttpClient


class AgentsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Agent]:
        """List agents.

        Args:
            keyword: Filter by name substring.
            status: Filter by status. "published" matches both
                    "published" and "published_edited" on the backend.
            offset: Pagination offset (default 0).
            limit: Max items to return (default 50).
        """
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if keyword:
            params["name"] = keyword
        if status:
            params["publish_status"] = status

        data = self._http.get(
            "/api/agent-factory/v3/personal-space/agent-list", params=params
        )
        items = (
            data
            if isinstance(data, list)
            else (data.get("entries") or data.get("data") or [])
        )
        agents = [_parse_agent(d) for d in items]

        # If user asked for "published", also fetch "published_edited"
        if status == "published":
            params["publish_status"] = "published_edited"
            data2 = self._http.get(
                "/api/agent-factory/v3/personal-space/agent-list", params=params
            )
            items2 = (
                data2
                if isinstance(data2, list)
                else (data2.get("entries") or data2.get("data") or [])
            )
            seen = {a.id for a in agents}
            agents.extend(
                _parse_agent(d) for d in items2
                if str(d.get("id", "")) not in seen
            )

        return agents

    def get(self, id: str) -> Agent:
        data = self._http.get(f"/api/agent-factory/v3/agent/{id}")
        return _parse_agent(data)


def _parse_agent(d: Any) -> Agent:
    # Extract knowledge network IDs from config.data_source.kg
    kn_ids: list[str] = d.get("kn_ids", [])
    config = d.get("config") or {}
    if not kn_ids:
        ds = config.get("data_source") or {}
        kn_ids = [kg["kg_id"] for kg in (ds.get("kg") or []) if kg.get("kg_id")]
        kn_entry = (ds.get("kn_entry") or ds.get("knowledge_network")) or {}
        if isinstance(kn_entry, list):
            kn_ids.extend(e.get("id", "") for e in kn_entry if e.get("id"))

    # Map agent-factory status to simplified status
    raw_status = d.get("status", "unpublished")
    if raw_status in ("published", "published_edited"):
        status = "published"
    else:
        status = "draft"

    return Agent(
        id=str(d.get("id", "")),
        name=d.get("name", ""),
        key=d.get("key"),
        version=d.get("version"),
        description=d.get("profile") or d.get("description"),
        status=status,
        kn_ids=kn_ids,
        system_prompt=config.get("system_prompt") or d.get("system_prompt"),
        capabilities=d.get("capabilities", []),
        model_config_data=config.get("llms") or d.get("model_config"),
        conversation_count=d.get("conversation_count", 0),
    )
