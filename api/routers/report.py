"""
User Scam Reporting Endpoint: POST /v1/report
"""

import json
import uuid
from fastapi import APIRouter, Depends

from api.models import ReportRequest, ReportResponse
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore
from api.routers.assess import get_audit_store, get_feature_store

router = APIRouter(prefix="/v1", tags=["reports"])


@router.post("/report", response_model=ReportResponse)
def report_scam_payee(
    req: ReportRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store)
) -> ReportResponse:
    """
    Records user scam report and increments payee prior_reports_count. With the reporter's own case_id
    for this payee (reporting from a warning), that case is marked cancelled and reported.
    """
    report_id = f"rep-{uuid.uuid4().hex[:8]}"
    new_count = store.record_report(
        report_id=report_id,
        reporter_id=req.reporter_id,
        payee_vpa=req.payee_vpa,
        reason=req.reason,
        notes=req.notes
    )

    row = store.get_case(req.case_id) if req.case_id else None
    if row and row["user_id"] == req.reporter_id.strip().lower() \
            and row["payee_vpa"] == req.payee_vpa.strip().lower():
        store.update_case_decision(req.case_id, row["tier"], json.loads(row["reasons"] or "[]"), row["template_id"],
                                   int(row["hold_minutes"]), {"cancelled": True, "user_reported_scam": report_id})
        audit.append_log(case_id=req.case_id, user_id=row["user_id"], payee_vpa=row["payee_vpa"],
                         tier="user_reported_and_cancelled", reasons=["USER_REPORTED_SCAM"])

    return ReportResponse(
        status="success",
        report_id=report_id,
        payee_vpa=req.payee_vpa.strip().lower(),
        prior_reports_count=new_count
    )

