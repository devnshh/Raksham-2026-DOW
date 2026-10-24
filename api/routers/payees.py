"""
Payee Confirmation Endpoint: POST /v1/payees/{vpa}/confirm
Enforces dual-analyst confirmation rule before marking payee as scam.
"""

from fastapi import APIRouter, Depends

from api.models import ConfirmScamRequest, ConfirmScamResponse
from api.store.sqlite_store import SQLiteFeatureStore
from api.routers.assess import get_feature_store
from api.security import require_analyst_key

router = APIRouter(prefix="/v1", tags=["payees"], dependencies=[Depends(require_analyst_key)])


@router.post("/payees/{vpa}/confirm", response_model=ConfirmScamResponse)
def confirm_scam_payee(
    vpa: str,
    req: ConfirmScamRequest,
    store: SQLiteFeatureStore = Depends(get_feature_store)
) -> ConfirmScamResponse:
    """
    Analyst confirmation for scam payee.
    Requires TWO DISTINCT analyst IDs before taking effect (is_confirmed_scam=True).
    """
    clean_vpa = vpa.strip().lower()
    total_confirmations, is_confirmed = store.confirm_scam_payee(
        payee_vpa=clean_vpa,
        analyst_id=req.analyst_id,
        notes=req.notes
    )

    status = "analyst_confirmed_scam" if is_confirmed else "pending_second_analyst"

    return ConfirmScamResponse(
        payee_vpa=clean_vpa,
        analyst_id=req.analyst_id,
        total_confirmations=total_confirmations,
        is_confirmed_scam=is_confirmed,
        status=status
    )

