"""
SubAgentRunner — loads and runs on-demand sub-agents from workspace/agents/{name}/.

Each sub-agent has:
  workspace/agents/{name}/SOUL.md      — persona + specialisation
  workspace/agents/{name}/tools.yaml   — list of tool names
  workspace/agents/{name}/memory/      — sub-agent's own memory

The main agent (MiniClaw) delegates to sub-agents and summarises results.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Optional

_DUBAI_TZ = timezone(timedelta(hours=4))


def _dubai_today():
    return datetime.now(_DUBAI_TZ).date()

import yaml

from src.gateway import config as cfg
from src.tools.claude_cli import call_claude, extract_text, ClaudeCLIError

if TYPE_CHECKING:
    from src.tools.registry import ToolRegistry

log = logging.getLogger(__name__)


@dataclass
class SubAgentDef:
    name: str
    soul: str              # content of SOUL.md
    tools: list[str]       # tool names this sub-agent uses
    memory_dir: Path
    purpose: str = ""


class SubAgentRunner:
    """Loads sub-agents from workspace/agents/ and delegates messages to them."""

    def __init__(self, workspace_dir: Path, tool_registry: "ToolRegistry"):
        self.workspace_dir = workspace_dir
        self.tool_registry = tool_registry
        self._agents: dict[str, SubAgentDef] = {}
        self.load()

    def load(self) -> None:
        """Scan workspace/agents/ and load all sub-agent definitions."""
        agents_dir = self.workspace_dir / "agents"
        if not agents_dir.exists():
            return

        self._agents = {}
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            soul_path = agent_dir / "SOUL.md"
            tools_path = agent_dir / "tools.yaml"
            if not soul_path.exists():
                continue

            soul = soul_path.read_text(encoding="utf-8")
            tools: list[str] = []
            purpose = ""

            if tools_path.exists():
                try:
                    data = yaml.safe_load(tools_path.read_text(encoding="utf-8")) or {}
                    tools = data.get("tools", [])
                    purpose = data.get("purpose", "")
                except yaml.YAMLError as e:
                    log.warning("Failed to parse tools.yaml for %s: %s", agent_dir.name, e)

            memory_dir = agent_dir / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)

            self._agents[agent_dir.name] = SubAgentDef(
                name=agent_dir.name,
                soul=soul,
                tools=tools,
                memory_dir=memory_dir,
                purpose=purpose,
            )
            log.info("Loaded sub-agent: %s (tools: %s)", agent_dir.name, tools)

    def all(self) -> list[SubAgentDef]:
        return list(self._agents.values())

    def create(
        self,
        name: str,
        soul_content: str,
        tools: list[str],
        purpose: str = "",
    ) -> SubAgentDef:
        """Create a new sub-agent on disk and register it."""
        agent_dir = self.workspace_dir / "agents" / name
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "memory").mkdir(parents=True, exist_ok=True)

        (agent_dir / "SOUL.md").write_text(soul_content, encoding="utf-8")
        tools_data = {"tools": tools, "purpose": purpose}
        (agent_dir / "tools.yaml").write_text(
            yaml.dump(tools_data, default_flow_style=False), encoding="utf-8"
        )

        agent = SubAgentDef(
            name=name,
            soul=soul_content,
            tools=tools,
            memory_dir=agent_dir / "memory",
            purpose=purpose,
        )
        self._agents[name] = agent
        self._update_agents_registry(agent)
        log.info("Created sub-agent: %s", name)
        return agent

    def _update_agents_registry(self, agent: SubAgentDef) -> None:
        """Append sub-agent entry to workspace/AGENTS.md."""
        from datetime import date
        registry_path = self.workspace_dir / "AGENTS.md"
        if not registry_path.exists():
            return

        content = registry_path.read_text(encoding="utf-8")
        entry = (
            f"\n### {agent.name}\n"
            f"- **SOUL**: workspace/agents/{agent.name}/SOUL.md\n"
            f"- **Tools**: {agent.tools}\n"
            f"- **Memory**: workspace/agents/{agent.name}/memory/\n"
            f"- **Created**: {_dubai_today().isoformat()}\n"
            f"- **Purpose**: {agent.purpose}\n"
        )

        # Remove the "no sub-agents" placeholder if present
        content = content.replace(
            "*No sub-agents yet. MiniClaw will recommend one when it notices repeated specialised requests.*",
            "",
        )

        # Append after "## Sub-Agents" section
        marker = "## Sub-Agents"
        if marker in content:
            idx = content.index(marker) + len(marker)
            content = content[:idx] + "\n" + entry + content[idx:]
        else:
            content += entry

        registry_path.write_text(content, encoding="utf-8")

    async def maybe_delegate(
        self,
        message: str,
        session_id: Optional[str],
        main_system_prompt: str,
        force_complexity: Optional[str],
    ) -> Optional[dict]:
        """
        Keyword-match the message against sub-agent names/purposes.
        Returns a result dict if exactly one agent matches, None otherwise.
        No API calls — instant, no network dependency.
        """
        if not self._agents:
            return None

        msg_lower = message.lower()
        matched: list[SubAgentDef] = []

        for agent in self._agents.values():
            # Keywords: name parts + meaningful words from purpose (>3 chars)
            keywords: set[str] = set(re.split(r"[\s_\-]+", agent.name.lower()))
            keywords.update(
                w for w in re.split(r"\W+", agent.purpose.lower()) if len(w) > 3
            )
            if any(re.search(rf"\b{re.escape(kw)}\b", msg_lower) for kw in keywords if kw):
                matched.append(agent)

        # Delegate only on an unambiguous single match
        if len(matched) != 1:
            return None

        agent = matched[0]
        log.info("Delegating to sub-agent: %s (keyword match)", agent.name)
        return await self._run_sub_agent(agent, message, session_id, force_complexity)

    async def _run_sub_agent(
        self,
        agent: SubAgentDef,
        message: str,
        session_id: Optional[str],
        force_complexity: Optional[str],
    ) -> dict:
        """Run a sub-agent and return the result."""
        # Build system prompt from sub-agent's SOUL + tool list
        tools_block = "\n".join(
            f"- {t}" + (" ✅" if self.tool_registry.is_available(t) else " ❌ (not available)")
            for t in agent.tools
        )
        system_prompt = (
            f"{agent.soul}\n\n"
            f"## Your Tools\n{tools_block}\n\n"
            f"## Instructions\n"
            f"You are a specialised sub-agent of MiniClaw. "
            f"Handle this request and return a clear, direct answer."
        )

        model = "sonnet" if (force_complexity or "medium") != "complex" else "opus"
        try:
            loop = asyncio.get_event_loop()
            fn = partial(
                call_claude,
                message,
                session_id=session_id,
                model=model,
                system_prompt=system_prompt,
                timeout=cfg.claude_timeout(),
            )
            response = await loop.run_in_executor(None, fn)
            text = extract_text(response)
            return {
                "text": text,
                "model_used": f"claude/{model}",
                "agent": agent.name,
                "session_id": response.get("session_id") or session_id,
            }
        except ClaudeCLIError as e:
            log.error("Sub-agent %s failed: %s", agent.name, e)
            return {
                "text": f"Sub-agent {agent.name} failed: {e}",
                "model_used": "error",
                "agent": agent.name,
                "session_id": session_id,
            }

    def as_system_prompt_block(self) -> str:
        if not self._agents:
            return ""
        lines = ["## Active Sub-Agents"]
        for a in self._agents.values():
            tools_str = ", ".join(a.tools) if a.tools else "none"
            lines.append(f"- **{a.name}**: {a.purpose} (tools: {tools_str})")
        lines.append(
            "\nDelegate to sub-agents when their specialisation matches the request. "
            "Summarise their results for Esam."
        )
        return "\n".join(lines)
