"""Skill: discover_agents — discover Decision Agents on the platform."""

from __future__ import annotations

from typing import Any

from kweaver.skills._base import BaseSkill


class DiscoverAgentsSkill(BaseSkill):
    def _execute(self, **kwargs: Any) -> dict[str, Any]:
        mode: str = kwargs["mode"]

        if mode == "list":
            return self._list(kwargs)
        elif mode == "detail":
            return self._detail(kwargs)
        else:
            return {"error": True, "message": f"未知模式: {mode}"}

    def _list(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        keyword = kwargs.get("keyword")
        status = kwargs.get("status", "published")
        agents = self.client.agents.list(keyword=keyword, status=status)

        result_agents = []
        for agent in agents:
            kn_names = []
            for kn_id in agent.kn_ids:
                try:
                    kn = self.client.knowledge_networks.get(kn_id)
                    kn_names.append(kn.name)
                except Exception:
                    kn_names.append(kn_id)
            result_agents.append({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "status": agent.status,
                "knowledge_networks": kn_names,
            })
        return {"agents": result_agents}

    def _detail(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        agent_id = self._resolve_agent_id(kwargs)
        if agent_id is None:
            return {"error": True, "message": "未找到指定的 Agent"}

        agent = self.client.agents.get(agent_id)

        kn_details = []
        for kn_id in agent.kn_ids:
            try:
                kn = self.client.knowledge_networks.get(kn_id)
                kn_details.append({"id": kn.id, "name": kn.name})
            except Exception:
                kn_details.append({"id": kn_id, "name": kn_id})

        prompt_preview = None
        if agent.system_prompt:
            prompt_preview = agent.system_prompt[:200]

        return {
            "agent": {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "status": agent.status,
                "knowledge_networks": kn_details,
                "prompts": {"system_prompt_preview": prompt_preview},
                "capabilities": agent.capabilities,
                "conversation_count": agent.conversation_count,
            }
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
