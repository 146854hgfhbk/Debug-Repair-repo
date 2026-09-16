#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ENV_FILE="${DEBUGREPAIR_ENV_FILE:-$SCRIPT_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Configuration file not found: $ENV_FILE" >&2
  echo "Create it with: cp .env.example .env" >&2
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

if [[ -n "${DEBUGREPAIR_PYTHON:-}" ]]; then
  PYTHON="$DEBUGREPAIR_PYTHON"
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON="$SCRIPT_DIR/.venv/bin/python"
else
  PYTHON="python3"
fi

cd "$SCRIPT_DIR"
exec "$PYTHON" src/client.py "$@"
