"""
Skill creator — agents can call this to write new SKILL.md files and register them.
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

from src.skills.loader import Skill
from src.skills.registry import SkillRegistry

log = logging.getLogger(__name__)


class SkillCreator:
    def __init__(self, skills_dir: Path, registry: SkillRegistry):
        self.skills_dir = skills_dir
        self.registry = registry

    def create(
        self,
        name: str,
        description: str,
        tools: list[str],
        triggers: list[str],
        body: str,
    ) -> Skill:
        """
        Write a new SKILL.md and register it.
        Overwrites if the skill already exists.
        """
        skill_dir = self.skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        fm = {
            "name": name,
            "description": description,
            "tools": tools,
            "trigger": ", ".join(triggers),
        }
        content = f"---\n{yaml.dump(fm, default_flow_style=False)}---\n\n{body.strip()}\n"
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content, encoding="utf-8")
        log.info("Created skill: %s at %s", name, skill_file)

        # Hot-reload the registry
        self.registry.reload()
        skill = self.registry.get(name)
        if skill is None:
            raise RuntimeError(f"Skill '{name}' was written but not loaded — check SKILL.md syntax")
        return skill

    def delete(self, name: str) -> bool:
        """Delete a skill directory and reload the registry."""
        skill_dir = self.skills_dir / name
        if not skill_dir.exists():
            return False
        import shutil
        shutil.rmtree(skill_dir)
        self.registry.reload()
        log.info("Deleted skill: %s", name)
        return True
