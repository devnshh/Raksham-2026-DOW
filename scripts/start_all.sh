#!/usr/bin/env bash
# Satark launcher for macOS / Linux: Model Service (8001), waits for health, then Risk API (8000).
# Run from anywhere inside an activated virtualenv:  pip install -r requirements.txt
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# Shared secret between the services and the analyst key: env value if set, else generated per run.
export MODEL_SERVICE_KEY="${MODEL_SERVICE_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')}"
export SATARK_ANALYST_KEY="${SATARK_ANALYST_KEY:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')}"
echo "Analyst API key (X-API-Key): $SATARK_ANALYST_KEY"

python3 -m uvicorn model_service.main:app --host 127.0.0.1 --port 8001 &
MODEL_PID=$!
trap 'kill $MODEL_PID 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8001/health >/dev/null; then echo "Model Service ready"; break; fi
  sleep 0.5
done

MODEL_SERVICE_URL="http://127.0.0.1:8001" python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
