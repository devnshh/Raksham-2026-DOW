"""
Case Management Endpoints: GET /v1/cases, GET /v1/cases/{id}
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from api.models import CaseResponse, ConfirmScamRequest
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore
from api.routers.assess import get_audit_store, get_feature_store, hold_ends_at
from api.security import acting_analyst, require_analyst_key

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
                dispute=evidence.get("dispute"),
                hold_active=hold_ends_at(r) is not None
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
        hold_active=hold_ends_at(row) is not None,
        evidence_pack=evidence_pack
    )


@router.post("/cases/{case_id}/release")
def release_hold(
    case_id: str,
    req: ConfirmScamRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store),
    bound: Optional[str] = Depends(require_analyst_key)
) -> Dict[str, Any]:
    """An analyst ends a red pause early after checking with the user (for example on a call back),
    so this payment can go ahead. Logged in the audit chain. The next risk check for the payee is
    a fresh one and can pause again."""
    row = store.get_case(case_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    analyst = acting_analyst(bound, req.analyst_id)
    if hold_ends_at(row) is None:
        raise HTTPException(status_code=409, detail="This case has no safety hold running")
    store.update_case_decision(case_id, row["tier"], json.loads(row["reasons"] or "[]"), row["template_id"],
                               int(row["hold_minutes"]),
                               {"hold_released_by": analyst, "hold_released_at": datetime.now(timezone.utc).isoformat()})
    audit.append_log(case_id=case_id, user_id=f"analyst:{analyst}", payee_vpa=row["payee_vpa"],
                     tier="analyst_release_hold", reasons=["HOLD_RELEASED"])
    return {"case_id": case_id, "hold_released_by": analyst}



@router.post("/cases/{case_id}/accept-appeal")
def accept_appeal(
    case_id: str,
    req: ConfirmScamRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store),
    bound: Optional[str] = Depends(require_analyst_key)
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
    analyst = acting_analyst(bound, req.analyst_id)
    features = json.loads(row["feature_vector"] or "{}")
    store.trust_pair(row["user_id"], row["payee_vpa"], "analyst", case_id, features.get("payee_reports_prior") or 0)
    updates = {"dispute": "false_alarm_accepted", "appeal_accepted_by": analyst}
    if hold_ends_at(row):
        # Accepting the appeal also ends this case's pause, so the next check is fresh.
        updates.update(hold_released_by=analyst,
                       hold_released_at=datetime.now(timezone.utc).isoformat())
    store.update_case_decision(case_id, row["tier"], json.loads(row["reasons"] or "[]"), row["template_id"],
                               int(row["hold_minutes"]), updates)
    audit.append_log(case_id=case_id, user_id=f"analyst:{analyst}",
                     payee_vpa=row["payee_vpa"], tier="analyst_accept_appeal", reasons=["APPEAL_ACCEPTED"])
    return {"case_id": case_id, "dispute": "false_alarm_accepted", "payee_still_declined": row["tier"] == "decline"}
