"""
Health Check Endpoint: GET /health
"""

from fastapi import APIRouter, Depends

from api.models import HealthResponse
from api.store.audit_store import AuditLogStore
from api.policy.engine import PolicyEngine
from api.routers.assess import get_audit_store, get_policy_engine
from api.config import MODEL_VERSION

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(
    audit: AuditLogStore = Depends(get_audit_store),
    policy: PolicyEngine = Depends(get_policy_engine)
) -> HealthResponse:
    """Returns system status, database health, and audit chain verification."""
    is_valid, count, msg = audit.verify_chain()
    audit_status = "intact" if is_valid else f"corrupted: {msg}"

    return HealthResponse(
        status="ok",
        database="healthy",
        audit_chain=f"{audit_status} ({count} entries)",
        policy_version=str(policy.config.get("version", "1.0.0")),
        model_version=MODEL_VERSION
    )

