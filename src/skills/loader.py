"""
Skill loader — scans workspace/skills/*/SKILL.md and parses each into a Skill object.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


@dataclass
class Skill:
    name: str
    description: str
    tools: list[str]
    triggers: list[str]
    body: str          # full content after frontmatter
    path: Path

    @property
    def system_prompt_block(self) -> str:
        return f"## Skill: {self.name}\n{self.body}"


def _parse(path: Path) -> Skill | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception as e:
        log.warning("Cannot read %s: %s", path, e)
        return None

    # Split on frontmatter delimiters
    parts = raw.split("---", 2)
    if len(parts) >= 3:
        try:
            fm = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            fm = {}
        body = parts[2].strip()
    else:
        fm = {}
        body = raw.strip()

    # Parse triggers — can be a string "a, b, c" or a list
    raw_triggers = fm.get("trigger", "")
    if isinstance(raw_triggers, list):
        triggers = [str(t).strip() for t in raw_triggers]
    else:
        triggers = [t.strip() for t in str(raw_triggers).split(",") if t.strip()]

    tools = fm.get("tools", [])
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",")]

    return Skill(
        name=fm.get("name", path.parent.name),
        description=fm.get("description", ""),
        tools=tools,
        triggers=triggers,
        body=body,
        path=path,
    )


def load_all(skills_dir: Path) -> list[Skill]:
    """Scan skills_dir/*/SKILL.md and return all successfully parsed Skills."""
    if not skills_dir.exists():
        return []
    skills = []
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        skill = _parse(skill_file)
        if skill:
            skills.append(skill)
            log.debug("Loaded skill: %s (%d triggers)", skill.name, len(skill.triggers))
    log.info("Loaded %d skills from %s", len(skills), skills_dir)
    return skills
