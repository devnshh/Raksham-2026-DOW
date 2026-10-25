"""
Case Management Endpoints: GET /v1/cases, GET /v1/cases/{id}
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from api.config import THRESHOLDS_PATH
from api.models import CaseResponse, ConfirmScamRequest
from api.policy.engine import PolicyEngine
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore
from api.routers.assess import case_state, get_audit_store, get_feature_store, get_policy_engine, hold_ends_at
from api.security import acting_analyst, require_analyst_key

router = APIRouter(prefix="/v1", tags=["cases"], dependencies=[Depends(require_analyst_key)])


def _status(evidence: Dict[str, Any]) -> str:
    return case_state(evidence)


def _hold_shown(row: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
    """A hold the console counts down. After the user cancels, the pause still covers retries, but
    there is no payment waiting on it."""
    return hold_ends_at(row) is not None and not evidence.get("cancelled_by_user")


@router.get("/cases", response_model=List[CaseResponse])
def list_cases(
    tier: Optional[str] = Query(None, description="Filter by risk tier: red, amber, green, decline"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    store: SQLiteFeatureStore = Depends(get_feature_store)
) -> List[CaseResponse]:
    """Lists recorded risk assessment cases."""
    rows = store.list_cases(tier=tier, limit=limit, offset=offset)
    scam_payees = store.confirmed_scam_payees(list({r["payee_vpa"] for r in rows}))

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
                hold_active=_hold_shown(r, evidence),
                payee_confirmed_scam=r["payee_vpa"] in scam_payees
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
        hold_active=_hold_shown(row, evidence_pack),
        payee_confirmed_scam=bool(store.confirmed_scam_payees([row["payee_vpa"]])),
        evidence_pack=evidence_pack
    )


@router.get("/console/summary")
def console_summary(
    hours: int = Query(24, ge=1, le=168),
    store: SQLiteFeatureStore = Depends(get_feature_store),
    policy: PolicyEngine = Depends(get_policy_engine)
) -> Dict[str, Any]:
    """Totals and an hourly series for the analyst console header and charts, plus the model cut-offs."""
    now = datetime.now(timezone.utc)
    rows = store.cases_since(hours)
    hourly = [{"hour_start": (now - timedelta(hours=h)).replace(minute=0, second=0, microsecond=0).isoformat(),
               "checks": 0, "warnings": 0, "red": 0, "decline": 0} for h in range(11, -1, -1)]
    totals = {"checks": len(rows), "green": 0, "amber": 0, "red": 0, "decline": 0, "holds_running": 0,
              "disputes_pending": 0, "money_held": 0.0, "payers": len({r["user_id"] for r in rows})}
    for r in rows:
        ev = json.loads(r["evidence_pack"] or "{}")
        totals[r["tier"]] = totals.get(r["tier"], 0) + 1
        totals["holds_running"] += _hold_shown(r, ev)
        totals["disputes_pending"] += ev.get("dispute") == "false_alarm_pending"
        if r["tier"] in ("red", "decline") and not ev.get("completed"):
            totals["money_held"] += float(r["amount"])
        age_h = int((now - datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))).total_seconds() // 3600)
        if age_h < 12:
            slot = hourly[11 - age_h]
            slot["checks"] += 1
            slot["warnings"] += r["tier"] in ("amber", "red")
            slot["red"] += r["tier"] == "red"
            slot["decline"] += r["tier"] == "decline"
    totals["warnings"] = totals["amber"] + totals["red"]
    try:
        thr = json.loads(Path(THRESHOLDS_PATH).read_text())
        cutoffs = {"amber": thr["amber"], "red": thr["red"]}
    except Exception:
        cutoffs = None
    return {"generated_at": now.isoformat(), "hours": hours, "totals": totals, "hourly": hourly, "cutoffs": cutoffs,
            "family_thresholds": policy.config.get("family_thresholds", {}),
            "hold_minutes": int(policy.config.get("hold_minutes", 30)), "demo_reset": _demo_reset_allowed()}


def _demo_reset_allowed() -> bool:
    """Only the demo start scripts turn this on, so a real deployment cannot be wiped from a browser."""
    return os.getenv("SATARK_ALLOW_DEMO_RESET") == "1"


@router.post("/console/reset")
def reset_demo(store: SQLiteFeatureStore = Depends(get_feature_store)) -> Dict[str, Any]:
    """Deletes every case, payment, report and hold, then reseeds the demo data (same as
    scripts/reset_demo_db.py). Refused unless SATARK_ALLOW_DEMO_RESET=1."""
    if not _demo_reset_allowed():
        raise HTTPException(status_code=403, detail="Demo reset is turned off on this server")
    from scripts.reset_demo_db import reset
    reset(store.db_path)
    return {"status": "reset"}


@router.get("/users/{user_id}/amounts")
def user_amounts(user_id: str, store: SQLiteFeatureStore = Depends(get_feature_store)) -> Dict[str, Any]:
    """The payer's recent completed payment amounts, for the "usual amounts" chart."""
    payments = store.recent_amounts(user_id)
    amounts = [a for a, _ in payments]
    ordered = sorted(amounts)
    median = ordered[len(ordered) // 2] if ordered else None
    return {"user_id": user_id.strip().lower(), "amounts": amounts, "median": median,
            "payments": [{"amount": a, "at": datetime.fromtimestamp(t / 1000, timezone.utc).isoformat()} for a, t in payments]}


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
