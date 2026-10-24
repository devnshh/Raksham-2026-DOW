"""
Case Management Endpoints: GET /v1/cases, GET /v1/cases/{id}
"""

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from api.models import CaseResponse, ConfirmScamRequest
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore
from api.routers.assess import get_audit_store, get_feature_store
from api.security import require_analyst_key

router = APIRouter(prefix="/v1", tags=["cases"], dependencies=[Depends(require_analyst_key)])


def _status(evidence: Dict[str, Any]) -> str:
    return "completed" if evidence.get("completed") else "cancelled" if evidence.get("cancelled") else "open"


@router.get("/cases", response_model=List[CaseResponse])
def list_cases(
    tier: Optional[str] = Query(None, description="Filter by risk tier: red, amber, green, decline"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: SQLiteFeatureStore = Depends(get_feature_store)
) -> List[CaseResponse]:
    """Lists recorded risk assessment cases."""
    rows = store.list_cases(tier=tier, limit=limit, offset=offset)

    results: List[CaseResponse] = []
    for r in rows:
        try:
            reasons = json.loads(r["reasons"] or "[]")
        except Exception:
            reasons = []
        try:
            evidence = json.loads(r["evidence_pack"] or "{}")
        except Exception:
            evidence = {}

        results.append(
            CaseResponse(
                case_id=r["case_id"],
                user_ref=r["user_id"],
                payee_vpa=r["payee_vpa"],
                amount=float(r["amount"]),
                tier=r["tier"],
                reasons=reasons,
                template_id=r["template_id"],
                hold_minutes=int(r["hold_minutes"]),
                created_at=r["created_at"],
                status=_status(evidence),
                dispute=evidence.get("dispute")
            )
        )

    return results


@router.get("/cases/{case_id}", response_model=CaseResponse)
def get_case_evidence(
    case_id: str,
    store: SQLiteFeatureStore = Depends(get_feature_store)
) -> CaseResponse:
    """Returns evidence pack for a specific case."""
    row = store.get_case(case_id)

    if not row:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    try:
        reasons = json.loads(row["reasons"] or "[]")
    except Exception:
        reasons = []

    try:
        evidence_pack = json.loads(row["evidence_pack"] or "{}")
    except Exception:
        evidence_pack = {}

    return CaseResponse(
        case_id=row["case_id"],
        user_ref=row["user_id"],
        payee_vpa=row["payee_vpa"],
        amount=float(row["amount"]),
        tier=row["tier"],
        reasons=reasons,
        template_id=row["template_id"],
        hold_minutes=int(row["hold_minutes"]),
        created_at=row["created_at"],
        status=_status(evidence_pack),
        dispute=evidence_pack.get("dispute"),
        evidence_pack=evidence_pack
    )



@router.post("/cases/{case_id}/accept-appeal")
def accept_appeal(
    case_id: str,
    req: ConfirmScamRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store)
) -> Dict[str, Any]:
    """An analyst accepts a user's false-alarm report: later red or amber checks for this user and
    payee turn green (not during a call or remote session, and only until the payee is reported
    again). A declined payee stays declined until it is cleared for everyone."""
    row = store.get_case(case_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    evidence = json.loads(row["evidence_pack"] or "{}")
    if evidence.get("dispute") != "false_alarm_pending":
        raise HTTPException(status_code=409, detail="This case has no false-alarm report waiting for review")
    features = json.loads(row["feature_vector"] or "{}")
    store.trust_pair(row["user_id"], row["payee_vpa"], "analyst", case_id, features.get("payee_reports_prior") or 0)
    store.update_case_decision(case_id, row["tier"], json.loads(row["reasons"] or "[]"), row["template_id"],
                               int(row["hold_minutes"]),
                               {"dispute": "false_alarm_accepted", "appeal_accepted_by": req.analyst_id})
    audit.append_log(case_id=case_id, user_id=f"analyst:{req.analyst_id.strip().lower()}",
                     payee_vpa=row["payee_vpa"], tier="analyst_accept_appeal", reasons=["APPEAL_ACCEPTED"])
    return {"case_id": case_id, "dispute": "false_alarm_accepted", "payee_still_declined": row["tier"] == "decline"}
