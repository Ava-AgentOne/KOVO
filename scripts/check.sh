#!/usr/bin/env bash
# Local CI (v3.0 offline dev) — run before every deploy.
# Substitutes for GitHub Actions while development stays off GitHub;
# the Actions workflow ships with the v3.0 release.
#
# Usage: bash scripts/check.sh          (from the repo root)
set -u

KOVO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KOVO_DIR"
FAIL=0

step() { echo; echo "== $1 =="; }

step "shell syntax (bash -n)"
for f in bootstrap.sh scripts/*.sh; do
    if bash -n "$f" 2>&1; then echo "  ok: $f"; else echo "  FAIL: $f"; FAIL=1; fi
done

step "python tests"
PY="venv/bin/python"
[ -x "$PY" ] || PY="python3"
if "$PY" -m pytest tests/ -q; then :; else FAIL=1; fi

step "gateway import"
if "$PY" -c "import src.gateway.main" >/dev/null 2>&1; then
    echo "  ok: src.gateway.main imports"
else
    echo "  FAIL: gateway import"; FAIL=1
fi

step "frontend build"
if (cd src/dashboard/frontend && npm run build --silent >/dev/null 2>&1); then
    echo "  ok: vite build"
else
    echo "  FAIL: frontend build"; FAIL=1
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED"
else
    echo "❌ CHECKS FAILED"
fi
exit "$FAIL"
