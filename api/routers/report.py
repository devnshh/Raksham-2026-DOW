"""
User Scam Reporting Endpoint: POST /v1/report
"""

import uuid
from fastapi import APIRouter, Depends

from api.models import ReportRequest, ReportResponse
from api.store.sqlite_store import SQLiteFeatureStore
from api.routers.assess import get_feature_store

router = APIRouter(prefix="/v1", tags=["reports"])


@router.post("/report", response_model=ReportResponse)
def report_scam_payee(
    req: ReportRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store)
) -> ReportResponse:
    """
    Records user scam report and increments payee prior_reports_count.
    """
    report_id = f"rep-{uuid.uuid4().hex[:8]}"
    new_count = store.record_report(
        report_id=report_id,
        reporter_id=req.reporter_id,
        payee_vpa=req.payee_vpa,
        reason=req.reason,
        notes=req.notes
    )

    return ReportResponse(
        status="success",
        report_id=report_id,
        payee_vpa=req.payee_vpa.strip().lower(),
        prior_reports_count=new_count
    )

