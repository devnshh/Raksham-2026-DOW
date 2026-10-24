"""
Pytest configuration and fixtures.
"""

import os

# Test-only secrets. The code has no hard-coded keys any more (see api/security.py),
# so the test session supplies its own before any app module is imported.
os.environ.setdefault("MODEL_SERVICE_KEY", "satark-internal-model-key-2026")
os.environ.setdefault("SATARK_ANALYST_KEY", "satark-internal-secret-2026")
ANALYST_HEADERS = {"X-API-Key": os.environ["SATARK_ANALYST_KEY"]}

import tempfile
import pytest
from typing import Generator
from fastapi.testclient import TestClient

from api.config import DB_PATH
from api.db.connection import init_db
from api.db.seed import seed_data
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore
from api.policy.engine import PolicyEngine
from api.policy.scorer import get_satark_scorer
from api.main import app
from api.routers.assess import get_feature_store, get_audit_store, get_policy_engine


@pytest.fixture(scope="session")
def test_db_path() -> Generator[str, None, None]:
    """Provides a temporary SQLite database path for isolated testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    init_db(path)
    seed_data(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def feature_store(test_db_path: str) -> SQLiteFeatureStore:
    return SQLiteFeatureStore(test_db_path)


@pytest.fixture
def audit_store(test_db_path: str) -> AuditLogStore:
    return AuditLogStore(test_db_path)


@pytest.fixture
def policy_engine() -> PolicyEngine:
    return PolicyEngine()


@pytest.fixture
def client(test_db_path: str) -> Generator[TestClient, None, None]:
    """Test client with overridden database dependencies."""
    store = SQLiteFeatureStore(test_db_path)
    audit = AuditLogStore(test_db_path)
    policy = PolicyEngine(scorer=get_satark_scorer())

    app.dependency_overrides[get_feature_store] = lambda: store
    app.dependency_overrides[get_audit_store] = lambda: audit
    app.dependency_overrides[get_policy_engine] = lambda: policy

    # Analyst endpoints (/v1/cases, /v1/payees) now require the analyst key.
    with TestClient(app, headers=ANALYST_HEADERS) as test_client:
        yield test_client

    app.dependency_overrides.clear()

