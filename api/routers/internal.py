"""
Internal Analyst & Operational Endpoints for SATARK Backend.
Protected by the analyst API key (SATARK_ANALYST_KEY), see api/security.py.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from api.store.sqlite_store import SQLiteFeatureStore
from api.routers.assess import get_feature_store
from api.security import require_analyst_key

router = APIRouter(prefix="/internal", tags=["internal"])

class ScamRegistryConfirmRequest(BaseModel):
    vpa: str = Field(..., description="Target UPI VPA to confirm/report as scam mule")
    source: Optional[str] = Field("analyst", description="Origin of confirmation: analyst|law_enforcement|cyber_cell")
    notes: Optional[str] = Field("", description="Operational or investigation notes")


class ScamRegistryConfirmResponse(BaseModel):
    status: str = "confirmed"
    vpa: str
    report_count: int
    confirmed_at: str
    source: str


@router.post(
    "/scam-registry",
    response_model=ScamRegistryConfirmResponse,
    dependencies=[Depends(require_analyst_key)]
)
def confirm_scam_mule(
    req: ScamRegistryConfirmRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store)
) -> ScamRegistryConfirmResponse:
    """
    Analyst Console Write Path: Confirms or flags a mule payee in scam_registry.
    Increments report_count so subsequent payments to this VPA compute a higher
    payee_reports_prior feature and score higher in the Satark fusion model.
    """
    clean_vpa = req.vpa.strip().lower()
    new_report_count = store.upsert_scam_registry(
        vpa=clean_vpa,
        source=req.source or "analyst"
    )
    now_iso = datetime.now(timezone.utc).isoformat()

    return ScamRegistryConfirmResponse(
        status="confirmed",
        vpa=clean_vpa,
        report_count=new_report_count,
        confirmed_at=now_iso,
        source=req.source or "analyst"
    )
