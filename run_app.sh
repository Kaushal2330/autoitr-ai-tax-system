#!/usr/bin/env bash
# Run AutoITR app using the virtualenv python without interactive activation.
set -e

# Resolve script directory (project root)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Candidate venv python paths (Windows and Unix)
PY_WIN="$DIR/.venv/Scripts/python.exe"
PY_UNIX="$DIR/.venv/bin/python"
PY_SYSTEM="$(which python3 2>/dev/null || which python 2>/dev/null || true)"

if [ -x "$PY_WIN" ]; then
  PY="$PY_WIN"
elif [ -x "$PY_UNIX" ]; then
  PY="$PY_UNIX"
elif [ -n "$PY_SYSTEM" ]; then
  PY="$PY_SYSTEM"
else
  echo "No python interpreter found. Create and populate .venv or install Python system-wide."
  exit 1
fi

echo "Using python: $PY"
cd "$DIR"
exec "$PY" app_enhanced.py