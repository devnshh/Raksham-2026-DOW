"""
SATARK Backend Application Entrypoint.
FastAPI application serving risk assessment, policy, reports, and evidence management.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from api.config import DB_PATH, POLICY_VERSION
from api.security import analyst_key
from api.db.seed import seed_data
from api.policy.scorer import get_satark_scorer
from api.routers import (
    assess_router,
    cases_router,
    payees_router,
    report_router,
    policy_router,
    health_router,
    internal_router,
    console_router,
    eval_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and seed database (no-op if already seeded)
    seed_data(DB_PATH)
    analyst_key()  # logs a generated key once if SATARK_ANALYST_KEY is unset
    # Preload SatarkScorer model once at startup
    get_satark_scorer()
    yield
    # Shutdown logic if any


logger = logging.getLogger("satark.api")

app = FastAPI(
    title="SATARK Scam-Interruption Risk API",
    description="Real-time UPI scam & coercion detection backend for RAKSHAM Hackathon Track 02.",
    version=POLICY_VERSION,
    lifespan=lifespan
)

# CORS: the Android app does not need it. Only browser tools listed in
# SATARK_CORS_ORIGINS (comma-separated) may call the API from a web page.
_cors_origins = [o.strip() for o in os.getenv("SATARK_CORS_ORIGINS", "").split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key", "Authorization"],
    )

# Include routers
app.include_router(health_router)
app.include_router(assess_router)
app.include_router(cases_router)
app.include_router(payees_router)
app.include_router(report_router)
app.include_router(policy_router)
app.include_router(internal_router)
app.include_router(console_router)
app.include_router(eval_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Fallback handler: logs the error server-side, never leaks internals to the client."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

