"""
Skill registry — in-memory index of loaded skills with lookup and matching.
"""
from __future__ import annotations

import logging
from pathlib import Path

from src.skills.loader import Skill, load_all

log = logging.getLogger(__name__)


class SkillRegistry:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        """Reload all skills from disk."""
        skills = load_all(self.skills_dir)
        self._skills = {s.name: s for s in skills}
        log.info("Registry has %d skills: %s", len(self._skills), list(self._skills))

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def match(self, message: str) -> list[Skill]:
        """Return skills whose trigger keywords appear in the message."""
        msg = message.lower()
        matched = []
        for skill in self._skills.values():
            if any(t in msg for t in skill.triggers):
                matched.append(skill)
        return matched

    def match_best(self, message: str) -> "Skill | None":
        """Return the single best-matching skill (most trigger hits), or None."""
        msg = message.lower()
        best: "Skill | None" = None
        best_score = 0
        for skill in self._skills.values():
            score = sum(1 for t in skill.triggers if t in msg)
            if score > best_score:
                best_score = score
                best = skill
        return best if best_score > 0 else None

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def names(self) -> list[str]:
        return list(self._skills.keys())
