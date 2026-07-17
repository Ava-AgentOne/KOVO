"""Tests for the Add-ons engine (v3.0 Phase 3.5)."""
import json
import time
from unittest.mock import patch

import pytest

from src.tools import addons


# ── Catalog shape ─────────────────────────────────────────────────────────────

def test_catalog_entries_complete():
    ids = set()
    for entry in addons.catalog():
        ids.add(entry["id"])
        for key in ("id", "label", "desc", "category", "configure_kind", "docs"):
            assert entry.get(key), f"{entry['id']} missing {key}"
    assert ids == {"tailscale", "google_workspace", "ollama", "home_assistant"}


def test_get_known_and_unknown():
    assert addons.get("tailscale")["label"] == "Tailscale"
    assert addons.get("nope") is None


def test_install_commands_are_fixed_strings():
    # Show-before-run only makes sense if commands are static server-side.
    for cmd in addons.TAILSCALE_INSTALL + addons.OLLAMA_INSTALL:
        assert isinstance(cmd, str) and "{" not in cmd


# ── list_with_status ──────────────────────────────────────────────────────────

def test_list_with_status_strips_commands_and_marks_installable():
    fake = {"status": "not_installed"}
    with patch.dict(addons._DETECTORS,
                    {k: lambda: dict(fake) for k in addons._DETECTORS}):
        out = addons.list_with_status()
    by_id = {e["id"]: e for e in out}
    assert all("install_commands" not in e for e in out)
    assert by_id["google_workspace"]["installable"] is False
    assert by_id["home_assistant"]["installable"] is False
    if addons.IS_LINUX:
        assert by_id["tailscale"]["installable"] is True


def test_list_with_status_survives_detector_crash():
    with patch.dict(addons._DETECTORS,
                    {"tailscale": lambda: 1 / 0}):
        out = addons.list_with_status()
    ts = next(e for e in out if e["id"] == "tailscale")
    assert ts["status"] == "unknown"


# ── Detectors ─────────────────────────────────────────────────────────────────

def test_detect_tailscale_not_installed():
    with patch("shutil.which", return_value=None):
        assert addons._detect_tailscale()["status"] == "not_installed"


def test_detect_google_states(tmp_path, monkeypatch):
    monkeypatch.setenv("KOVO_DIR", str(tmp_path))
    (tmp_path / "config").mkdir()
    assert addons._detect_google()["status"] == "not_installed"

    (tmp_path / "config" / "google-credentials.json").write_text("{}")
    assert addons._detect_google()["status"] == "installed"

    (tmp_path / "config" / "google-token.json").write_text(
        json.dumps({"scopes": ["a", "b"]}))
    d = addons._detect_google()
    assert d["status"] == "ready" and "2 scopes" in d["detail"]


def test_detect_home_assistant(monkeypatch):
    from src.gateway import config as cfg
    with patch.object(cfg, "get", return_value={"mcp": {"home_assistant": {}}}):
        assert addons._detect_home_assistant()["status"] == "ready"
    with patch.object(cfg, "get", return_value={}):
        assert addons._detect_home_assistant()["status"] == "not_installed"


# ── Install job machinery ─────────────────────────────────────────────────────

def _reset_job():
    with addons._job_lock:
        addons._job.update(addon=None, state="idle", log=[])


def _wait_done(timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if addons.job_status()["state"] in ("done", "failed"):
            return addons.job_status()
        time.sleep(0.05)
    raise TimeoutError("install job never finished")


def test_run_install_success_and_log():
    _reset_job()
    addons._run_install("fake", ["echo hello", "true"])
    st = addons.job_status()
    assert st["state"] == "done"
    assert "$ echo hello" in st["log"] and "hello" in st["log"]


def test_run_install_stops_on_failure():
    _reset_job()
    addons._run_install("fake", ["false", "echo never"])
    st = addons.job_status()
    assert st["state"] == "failed"
    assert not any("never" in line for line in st["log"])
    assert any("exit 1" in line for line in st["log"])


def test_start_install_rejects_unknown_and_uninstallable():
    _reset_job()
    with pytest.raises(ValueError):
        addons.start_install("nope")
    with pytest.raises(ValueError):
        addons.start_install("google_workspace")  # config-only, no commands


def test_start_install_rejects_concurrent():
    _reset_job()
    with addons._job_lock:
        addons._job["state"] = "running"
    try:
        with pytest.raises(ValueError, match="already running"):
            with patch.object(addons, "get",
                              return_value={"install_commands": ["true"]}):
                addons.start_install("tailscale")
    finally:
        _reset_job()


# ── Ollama pull validation ────────────────────────────────────────────────────

def test_ollama_pull_validates_model_name():
    _reset_job()
    for bad in ("", "a b", "x; rm -rf /", "$(boom)", "a" * 81):
        with pytest.raises(ValueError):
            addons.ollama_pull(bad)


def test_ollama_pull_runs_job():
    _reset_job()
    with patch.object(addons.subprocess, "run") as m:
        m.return_value.returncode = 0
        m.return_value.stdout = "pulled"
        m.return_value.stderr = ""
        r = addons.ollama_pull("llama3.2:3b")
        assert r == {"started": True, "model": "llama3.2:3b"}
        st = _wait_done()
    assert st["state"] == "done"
    assert m.call_args[0][0] == "ollama pull llama3.2:3b"
    _reset_job()


# ── Google auth flow state ────────────────────────────────────────────────────

def test_google_auth_complete_requires_start():
    addons._google_flow = None
    with pytest.raises(ValueError, match="[Ss]tart"):
        addons.google_auth_complete("code")


def test_google_auth_start_and_complete():
    with patch("src.tools.google_api.start_auth_flow",
               return_value=("https://auth", "FLOW")):
        assert addons.google_auth_start() == {"auth_url": "https://auth"}
    assert addons._google_flow == "FLOW"
    with patch("src.tools.google_api.complete_auth_flow",
               return_value="✅ ok") as m:
        r = addons.google_auth_complete("some-code")
    assert r["ok"] is True
    assert m.call_args[0] == ("FLOW", "some-code")
    assert addons._google_flow is None  # cleared after success


def test_google_auth_complete_failure_keeps_flow():
    addons._google_flow = "FLOW"
    with patch("src.tools.google_api.complete_auth_flow",
               return_value="❌ Auth failed: nope"):
        r = addons.google_auth_complete("bad")
    assert r["ok"] is False
    assert addons._google_flow == "FLOW"  # retry allowed without restart
    addons._google_flow = None
