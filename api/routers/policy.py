"""
Policy Inspection Endpoint: GET /v1/policy
"""

from fastapi import APIRouter, Depends

from api.models import PolicyResponse
from api.policy.engine import PolicyEngine
from api.routers.assess import get_policy_engine

router = APIRouter(prefix="/v1", tags=["policy"])


@router.get("/policy", response_model=PolicyResponse)
def get_current_policy(
    policy: PolicyEngine = Depends(get_policy_engine)
) -> PolicyResponse:
    """Returns active versioned policy configuration and thresholds."""
    return PolicyResponse(
        version=str(policy.config.get("version", "1.0.0")),
        rules=policy.config
    )

