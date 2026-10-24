"""
Results page (plan 1.7):
- GET  /eval                 the page
- GET  /v1/eval/latest       the last logged holdout run, how many runs there were, its failure-case notes,
                             and the latest robustness run (ml/robustness.py) if there is one
- POST /v1/eval/fresh        generates a world from a seed nobody has used and scores it live

Fresh worlds run the same command as any evaluation (`ml/evaluate.py --role fresh`), leak tripwires
included, in a separate process, one at a time. That costs real CPU, so it needs the analyst key.
"""

import json
import logging
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api.security import require_analyst_key

_ROOT = Path(__file__).resolve().parents[2]
_RESULTS = _ROOT / "ml" / "results"
_LOG = _ROOT / "ml" / "eval_log.md"
_FIXED_SEEDS = {11, 22, 33}  # train, holdout, validation: never a "fresh" world
_fresh_lock = threading.Lock()
logger = logging.getLogger("satark.eval")

router = APIRouter(tags=["eval"])


class FreshWorldRequest(BaseModel):
    seed: int = Field(ge=1, le=10**9)
    users: int = Field(default=300, ge=100, le=1000)


@router.get("/eval", include_in_schema=False)
def eval_page() -> FileResponse:
    return FileResponse(_ROOT / "api" / "static" / "eval.html")


def _failure_notes(run: int) -> str:
    text = _LOG.read_text() if _LOG.exists() else ""
    m = re.search(rf"^## Run {run}: named failure cases\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


@router.get("/v1/eval/latest")
def latest_holdout_run() -> Dict[str, Any]:
    runs = sorted((int(m.group(1)), p) for p in _RESULTS.glob("holdout_run*.json")
                  if (m := re.fullmatch(r"holdout_run(\d+)\.json", p.name)))
    if not runs:
        raise HTTPException(status_code=404, detail="No holdout run has been logged yet (ml/evaluate.py --holdout)")
    n, path = runs[-1]
    robust = sorted(_RESULTS.glob("robustness_*.json"), key=lambda q: q.stat().st_mtime)
    return {"runs_logged": len(runs), "result": json.loads(path.read_text()), "failure_notes": _failure_notes(n),
            "robustness": json.loads(robust[-1].read_text()) if robust else None}


@router.post("/v1/eval/fresh", dependencies=[Depends(require_analyst_key)])
def fresh_world(req: FreshWorldRequest) -> Dict[str, Any]:
    if req.seed in _FIXED_SEEDS:
        raise HTTPException(status_code=409, detail=f"Seed {req.seed} is the train, validation or holdout world. Pick another.")
    if not _fresh_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Another fresh world is being scored. Try again in a minute.")
    try:
        run = subprocess.run(
            [sys.executable, "ml/evaluate.py", "--role", "fresh", "--seed", str(req.seed), "--users", str(req.users)],
            cwd=_ROOT, capture_output=True, text=True, timeout=180, env={**os.environ, "PYTHONPATH": str(_ROOT)},
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Scoring took longer than 3 minutes")
    finally:
        _fresh_lock.release()
    if run.returncode:
        logger.error("Fresh-world evaluation failed (seed %s):\n%s\n%s", req.seed, run.stdout, run.stderr)
        raise HTTPException(status_code=500, detail="Evaluation failed; see the server log")
    path = _RESULTS / f"fresh_seed{req.seed}_u{req.users}.json"
    result = json.loads(path.read_text())
    path.unlink()  # fresh worlds are shown once, not kept
    return result
