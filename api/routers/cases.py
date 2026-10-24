"""
Case Management Endpoints: GET /v1/cases, GET /v1/cases/{id}
"""

import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from api.models import CaseResponse
from api.store.sqlite_store import SQLiteFeatureStore
from api.routers.assess import get_feature_store
from api.security import require_analyst_key

router = APIRouter(prefix="/v1", tags=["cases"], dependencies=[Depends(require_analyst_key)])


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
            completed = bool(json.loads(r["evidence_pack"] or "{}").get("completed"))
        except Exception:
            completed = False

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
                status="completed" if completed else "open"
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
        status="completed" if evidence_pack.get("completed") else "open",
        evidence_pack=evidence_pack
    )

