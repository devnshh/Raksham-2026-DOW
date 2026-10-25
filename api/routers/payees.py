"""
Analyst payee endpoints:
- GET  /v1/payees/{vpa}          payee view: 24 h fan-in cluster, reports, confirmations, recent cases
- POST /v1/payees/{vpa}/confirm  dual-analyst confirmation before a payee is declined
- POST /v1/payees/{vpa}/clear    withdraws all confirmations
Confirm and clear are both written to the hash-chained audit log.
"""

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from api.models import ConfirmScamRequest, ConfirmScamResponse
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore
from api.routers.assess import get_audit_store, get_feature_store
from api.security import acting_analyst, require_analyst_key

router = APIRouter(prefix="/v1", tags=["payees"], dependencies=[Depends(require_analyst_key)])


def _audit_analyst_action(audit: AuditLogStore, action: str, vpa: str, analyst_id: str, reason: str) -> None:
    audit.append_log(case_id=f"a-{uuid.uuid4().hex[:8]}", user_id=f"analyst:{analyst_id.strip().lower()}",
                     payee_vpa=vpa, tier=action, reasons=[reason])


@router.get("/payees/{vpa}")
def payee_view(vpa: str, store: SQLiteFeatureStore = Depends(get_feature_store)) -> Dict[str, Any]:
    return store.payee_overview(vpa)


@router.post("/payees/{vpa}/confirm", response_model=ConfirmScamResponse)
def confirm_scam_payee(
    vpa: str,
    req: ConfirmScamRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store),
    bound: Optional[str] = Depends(require_analyst_key)
) -> ConfirmScamResponse:
    """
    Analyst confirmation for scam payee.
    Requires TWO DISTINCT analyst IDs before taking effect (is_confirmed_scam=True).
    """
    clean_vpa = vpa.strip().lower()
    analyst = acting_analyst(bound, req.analyst_id)
    total_confirmations, is_confirmed = store.confirm_scam_payee(
        payee_vpa=clean_vpa,
        analyst_id=analyst,
        notes=req.notes
    )
    _audit_analyst_action(audit, "analyst_confirm", clean_vpa, analyst, "ANALYST_CONFIRMATION")

    status = "analyst_confirmed_scam" if is_confirmed else "pending_second_analyst"

    return ConfirmScamResponse(
        payee_vpa=clean_vpa,
        analyst_id=analyst,
        total_confirmations=total_confirmations,
        is_confirmed_scam=is_confirmed,
        status=status
    )


@router.post("/payees/{vpa}/clear")
def clear_payee(
    vpa: str,
    req: ConfirmScamRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store),
    audit: AuditLogStore = Depends(get_audit_store),
    bound: Optional[str] = Depends(require_analyst_key)
) -> Dict[str, Any]:
    """One analyst can clear a payee: payments to it are no longer declined. Reports stay on record."""
    clean_vpa = vpa.strip().lower()
    analyst = acting_analyst(bound, req.analyst_id)
    withdrawn = store.clear_payee(clean_vpa)
    _audit_analyst_action(audit, "analyst_clear", clean_vpa, analyst, "ANALYST_CLEARED")
    return {"payee_vpa": clean_vpa, "analyst_id": analyst, "withdrawn_confirmations": withdrawn,
            "is_confirmed_scam": False, "status": "cleared"}
