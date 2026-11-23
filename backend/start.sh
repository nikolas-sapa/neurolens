#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then
  # torch has no wheels for very new Pythons, so prefer a known-supported interpreter
  PY="${PYTHON:-}"
  if [ -z "$PY" ]; then
    for candidate in python3.12 python3.11 python3; do
      if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
    done
  fi
  "$PY" -m venv .venv
  .venv/bin/pip install --upgrade pip
fi
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --host "::" --reload --port 8000
