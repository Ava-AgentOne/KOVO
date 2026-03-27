"""
ToolRegistry — reads workspace/TOOLS.md and tracks tool availability.

TOOLS.md uses YAML frontmatter to define tools.  The body is for humans.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)


@dataclass
class ToolDef:
    name: str
    status: str          # installed | not_installed | configured | not_configured
    description: str
    install_command: Optional[str] = None
    config_needed: Optional[str] = None

    @property
    def available(self) -> bool:
        return self.status in ("installed", "configured")

    def missing_message(self) -> str:
        """Return a human-readable message about what's needed to use this tool."""
        if self.status == "not_installed":
            cmd = self.install_command or "unknown"
            return (
                f"Tool **{self.name}** is not installed.\n"
                f"Install with: `{cmd}`\n"
                f"Want me to install it?"
            )
        if self.status == "not_configured":
            info = self.config_needed or "check the docs"
            return (
                f"Tool **{self.name}** is installed but not configured.\n"
                f"Action needed: {info}"
            )
        return ""


class ToolRegistry:
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self._tools: dict[str, ToolDef] = {}
        self.load()

    def load(self) -> None:
        """Parse YAML frontmatter from workspace/TOOLS.md."""
        tools_path = self.workspace_dir / "TOOLS.md"
        try:
            content = tools_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            log.warning("TOOLS.md not found at %s", tools_path)
            return

        # Extract YAML frontmatter between --- delimiters
        match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not match:
            log.warning("No YAML frontmatter found in TOOLS.md")
            return

        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError as e:
            log.error("Failed to parse TOOLS.md frontmatter: %s", e)
            return

        self._tools = {}
        for item in data.get("tools", []):
            t = ToolDef(
                name=item["name"],
                status=item.get("status", "not_installed"),
                description=item.get("description", ""),
                install_command=item.get("install_command"),
                config_needed=item.get("config_needed"),
            )
            self._tools[t.name] = t

        log.info("Loaded %d tools from TOOLS.md", len(self._tools))

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def all(self) -> list[ToolDef]:
        return list(self._tools.values())

    def available(self) -> list[ToolDef]:
        return [t for t in self._tools.values() if t.available]

    def is_available(self, name: str) -> bool:
        t = self._tools.get(name)
        return t is not None and t.available

    def update_status(self, name: str, status: str) -> None:
        """Update tool status and persist to TOOLS.md."""
        self.update_tool(name, status=status)

    def update_tool(self, name: str, **fields) -> None:
        """Update any tool fields (status, config_needed, description) and persist."""
        if name not in self._tools:
            log.warning("Unknown tool: %s", name)
            return
        t = self._tools[name]
        for key, val in fields.items():
            if hasattr(t, key):
                setattr(t, key, val)
        self._save()

    def _save(self) -> None:
        """Write current tool state back to TOOLS.md frontmatter."""
        tools_path = self.workspace_dir / "TOOLS.md"
        try:
            content = tools_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            content = ""

        # Build YAML for frontmatter
        tools_data = {
            "tools": [
                {
                    "name": t.name,
                    "status": t.status,
                    "description": t.description,
                    **({"install_command": t.install_command} if t.install_command else {"install_command": None}),
                    **({"config_needed": t.config_needed} if t.config_needed else {"config_needed": None}),
                }
                for t in self._tools.values()
            ]
        }
        new_frontmatter = "---\n" + yaml.dump(tools_data, default_flow_style=False) + "---"

        # Replace existing frontmatter or prepend
        if re.match(r"^---\n", content):
            body_start = content.index("---", 3) + 3
            body = content[body_start:]
        else:
            body = "\n" + content

        tools_path.write_text(new_frontmatter + body, encoding="utf-8")

    def as_system_prompt_block(self) -> str:
        """Format tool registry for inclusion in agent system prompts."""
        lines = ["## Available Tools"]
        for t in self._tools.values():
            status_icon = "✅" if t.available else "❌"
            lines.append(f"- {status_icon} **{t.name}**: {t.description}")
            if not t.available and t.install_command:
                lines.append(f"  - Install: `{t.install_command}`")
            if not t.available and t.config_needed:
                lines.append(f"  - Config needed: {t.config_needed}")
        lines.append(
            "\nWhen you need a tool that is ❌, tell the owner what's needed and ask if he wants you to install/configure it."
        )
        return "\n".join(lines)
