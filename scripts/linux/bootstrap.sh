#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
python3 - <<'PY'
import sys
if sys.version_info < (3,11): raise SystemExit("Python 3.11+ required")
PY
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,monitoring,mcp]'
export STUDIO_HOME="${STUDIO_HOME:-$HOME/.local/share/11vated-studio}"
studio init
studio doctor
