"""The Claude Code allowlist that bootstrap.sh pre-approves, and the one-time
v3.0.3 cleanup that removes commands able to run anything from existing installs."""
import json
import re
from pathlib import Path

import pytest

from src.tools import claude_cli

ROOT = Path(__file__).resolve().parents[1]


def _bootstrap_allowlist():
    script = (ROOT / "bootstrap.sh").read_text()
    start = script.index('cat > "$KOVO_DIR/.claude/settings.local.json" << EOF\n')
    body = script[start:].split("<< EOF\n", 1)[1].split("\nEOF\n", 1)[0]
    return script, json.loads(body.replace("$KOVO_DIR", "/opt/kovo"))["permissions"]["allow"]


def test_bootstrap_does_not_pre_approve_commands_that_run_anything():
    _, allow = _bootstrap_allowlist()
    for entry in claude_cli.UNRESTRICTED_DEFAULTS:
        assert entry not in allow


def test_bootstrap_reports_the_right_number_of_entries():
    script, allow = _bootstrap_allowlist()
    reported = re.search(r'ok "Claude Code permissions \((\d+) entries\)"', script)
    assert int(reported.group(1)) == len(allow)


@pytest.fixture
def install(tmp_path, monkeypatch):
    settings = tmp_path / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    marker = tmp_path / "data" / "allowlist-cleanup-v3.0.3"
    monkeypatch.setattr(claude_cli, "_SETTINGS_FILE", settings)
    monkeypatch.setattr(claude_cli, "_UNRESTRICTED_CLEANUP_MARKER", marker)

    class Install:
        def write(self, entries):
            settings.write_text(json.dumps({"permissions": {"allow": entries}}, indent=2) + "\n")

        def allow(self):
            return json.loads(settings.read_text())["permissions"]["allow"]

    inst = Install()
    inst.settings, inst.marker = settings, marker
    return inst


def test_cleanup_removes_only_those_entries(install):
    install.write(["Bash(cat *)", "Bash(docker *)", "Bash(env *)", "Bash(gh *)",
                   "Bash(source *)", "Bash(sudo *)", "Bash(xargs *)", "Edit(*)"])
    removed = claude_cli.drop_unrestricted_defaults()
    assert sorted(removed) == sorted(claude_cli.UNRESTRICTED_DEFAULTS)
    assert install.allow() == ["Bash(cat *)", "Bash(gh *)", "Edit(*)"]
    assert install.marker.exists()


def test_cleanup_runs_once_so_a_later_approval_sticks(install):
    install.write(["Bash(cat *)", "Bash(sudo *)"])
    assert claude_cli.drop_unrestricted_defaults() == ["Bash(sudo *)"]
    # The owner approves sudo again on Telegram, then KOVO restarts
    install.write(["Bash(cat *)", "Bash(sudo *)"])
    assert claude_cli.drop_unrestricted_defaults() == []
    assert install.allow() == ["Bash(cat *)", "Bash(sudo *)"]


def test_cleanup_leaves_an_already_clean_list_untouched(install):
    install.write(["Bash(cat *)", "Edit(*)"])
    before = install.settings.read_text()
    assert claude_cli.drop_unrestricted_defaults() == []
    assert install.settings.read_text() == before
    assert install.marker.exists()


def test_cleanup_without_a_settings_file(install):
    assert claude_cli.drop_unrestricted_defaults() == []
    assert install.marker.exists()


def test_cleanup_tries_again_when_the_file_cannot_be_read(install):
    install.settings.write_text("{not json")
    assert claude_cli.drop_unrestricted_defaults() == []
    assert not install.marker.exists()
