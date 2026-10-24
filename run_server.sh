#!/usr/bin/env bash
# Single-process Risk API (model runs in-process). For the two-service setup use scripts/start_all.sh.
# Requires an activated virtualenv with: pip install -r requirements.txt
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
export PYTHONPATH="${DIR}${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m uvicorn api.main:app --host "${SATARK_HOST:-0.0.0.0}" --port "${SATARK_PORT:-8000}" "$@"
