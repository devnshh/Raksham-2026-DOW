"""API routers package."""
from api.routers.assess import router as assess_router
from api.routers.cases import router as cases_router
from api.routers.payees import router as payees_router
from api.routers.report import router as report_router
from api.routers.policy import router as policy_router
from api.routers.health import router as health_router
from api.routers.internal import router as internal_router

__all__ = [
    "assess_router",
    "cases_router",
    "payees_router",
    "report_router",
    "policy_router",
    "health_router",
    "internal_router"
]

