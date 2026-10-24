"""
SATARK Model Service (Port 8001).
Standalone microservice dedicated to hosting and executing the Satark ML fusion model.
Isolated from public traffic; protected by internal API key header.
"""

import logging
import os
import secrets
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from model_service.satark_scorer import SatarkScorer

# Resolve paths relative to this file
_BASE_DIR = Path(__file__).resolve().parent
_MODEL_PATH = Path(os.getenv("SATARK_MODEL_PATH", str(_BASE_DIR / "models" / "satark_model.joblib")))
_THRESHOLDS_PATH = Path(os.getenv("SATARK_THRESHOLDS_PATH", str(_BASE_DIR / "models" / "thresholds.json")))


def _service_key() -> str:
    """Shared secret for X-Internal-Key. Read from MODEL_SERVICE_KEY; never a hard-coded default.
    If unset, a random key is generated for this process, so no caller can authenticate by accident."""
    global _GENERATED_KEY
    key = os.getenv("MODEL_SERVICE_KEY")
    if key:
        return key
    if _GENERATED_KEY is None:
        _GENERATED_KEY = secrets.token_urlsafe(24)
        logging.getLogger("satark.model_service").warning(
            "MODEL_SERVICE_KEY is not set; generated a one-time key: %s (set it for the Risk API too)", _GENERATED_KEY)
    return _GENERATED_KEY


_GENERATED_KEY = None

_scorer: Optional[SatarkScorer] = None


def get_scorer() -> SatarkScorer:
    """Lazy loader / accessor for the singleton SatarkScorer instance."""
    global _scorer
    if _scorer is None:
        if not _MODEL_PATH.exists():
            raise RuntimeError(f"Model file not found at {_MODEL_PATH}")
        _scorer = SatarkScorer(str(_MODEL_PATH), str(_THRESHOLDS_PATH) if _THRESHOLDS_PATH.exists() else None)
    return _scorer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload model at service startup
    get_scorer()
    _service_key()  # logs a generated key once if MODEL_SERVICE_KEY is unset
    yield


app = FastAPI(
    title="SATARK Model Service",
    description="Internal ML inference microservice for Satark fraud & coercion risk scoring.",
    version="1.0.0",
    lifespan=lifespan
)


class ScoreRequest(BaseModel):
    features: Dict[str, Any] = Field(..., description="Feature vector with simulator names + entry_channel")
    note_intent: Optional[str] = Field("none", description="Categorical note intent")


class ScoreResponse(BaseModel):
    fusion_score: float = Field(..., description="Predicted probability of fraud/coercion")
    tier_hint: Optional[str] = Field(None, description="Suggested tier based on threshold cutoffs: green|amber|red")
    reasons: List[str] = Field(default_factory=list, description="Top push factors contributing to risk")


@app.get("/health")
def health_check():
    """Returns 200 OK after the model has successfully loaded."""
    scorer = get_scorer()
    if scorer is None or not hasattr(scorer, "b"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model not loaded")
    return {
        "status": "ok",
        "service": "satark_model_service",
        "model_loaded": True,
        "thresholds": scorer.thr
    }


@app.get("/thresholds")
def get_thresholds():
    """Returns the alert budget thresholds."""
    scorer = get_scorer()
    return {"thresholds": scorer.thr}


@app.post("/score", response_model=ScoreResponse)
def score_payment(
    req: ScoreRequest,
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key")
):
    """
    Computes risk score and reasons for a payment feature vector.
    Enforces internal API key authentication and strict feature completeness.
    """
    # 1. Authenticate internal key
    if not x_internal_key or not secrets.compare_digest(x_internal_key, _service_key()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing or invalid X-Internal-Key header"
        )

    scorer = get_scorer()

    # 2. Score with SatarkScorer
    try:
        result = scorer.score(req.features, note_intent=req.note_intent or "none")
        return ScoreResponse(
            fusion_score=float(result["fusion_score"]),
            tier_hint=result.get("tier_hint"),
            reasons=list(result.get("reasons", []))
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        # Catch missing required features from _frame and return HTTP 422
        if "Missing features" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=err_msg
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )
    except Exception:
        logging.getLogger("satark.model_service").exception("Inference failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference execution failed"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("model_service.main:app", host="127.0.0.1", port=8001, reload=False)
