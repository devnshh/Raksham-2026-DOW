"""
Tests for Standalone Model Service & Multi-Service Satark Architecture.
Covers:
1. Contract tests: API & HttpModelClient against Model Service.
2. Failure tests: Model service down, timeout, wrong internal key, missing feature -> safe amber CHECK_UNAVAILABLE.
3. Parity test: LocalModelClient vs HttpModelClient score equivalence.
4. Latency benchmark: 200+ requests across both modes with p50 and p95 reporting.
"""

import time
import pytest
import numpy as np
import httpx
from fastapi.testclient import TestClient

from model_service.main import app as model_app
from api.main import app as risk_api_app
from api.model_client import (
    ModelClient,
    LocalModelClient,
    HttpModelClient,
    ModelServiceError,
    ModelValidationError,
    ModelConnectionError,
    ModelTimeoutError
)
from api.policy.engine import PolicyEngine
from api.routers.assess import get_policy_engine, get_feature_store, get_audit_store
from api.store.sqlite_store import SQLiteFeatureStore
from api.store.audit_store import AuditLogStore


@pytest.fixture
def sample_features():
    """Canonical complete feature vector for scoring."""
    return {
        "on_call": False,
        "caller_in_contacts": False,
        "screen_shared": False,
        "remote_app_present": False,
        "remote_app_new": False,
        "app_switches": 0,
        "typing_z": 0.1,
        "pause_z": 0.0,
        "pin_time_z": -0.2,
        "device_new": False,
        "failed_auth": 0,
        "payee_first_time": True,
        "payee_age_days": 180.0,
        "payee_verified": True,
        "payee_new_payers_24h": 1,
        "payee_reports_prior": 0,
        "lookalike_score": 0.0,
        "amount": 450.0,
        "amount_ratio": 1.0,
        "amount_z": 0.1,
        "amount_vs_max": 0.3,
        "hour": 14,
        "hour_familiarity": 0.8,
        "same_payee_count_24h": 0,
        "same_payee_sum_24h": 0.0,
        "escalation_ratio": 1.0,
        "baseline_ready": True,
        "entry_channel": "typed_vpa"
    }


@pytest.fixture
def http_model_client():
    """HttpModelClient wired to model_service via TestClient."""
    test_client = TestClient(model_app)
    return HttpModelClient(
        base_url="http://testserver",
        api_key="satark-internal-model-key-2026",
        client=test_client
    )


# -----------------------------------------------------------------------------
# 1. Contract Tests
# -----------------------------------------------------------------------------

def test_model_service_health():
    """Model service GET /health returns 200 with model_loaded=True."""
    client = TestClient(model_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["model_loaded"] is True
    assert "thresholds" in data


def test_model_service_rejects_missing_or_wrong_internal_key(sample_features):
    """Model service rejects unauthorized requests with HTTP 401."""
    client = TestClient(model_app)
    # Missing header
    resp = client.post("/score", json={"features": sample_features, "note_intent": "none"})
    assert resp.status_code == 401

    # Invalid header
    resp = client.post(
        "/score",
        json={"features": sample_features, "note_intent": "none"},
        headers={"X-Internal-Key": "invalid-secret-key"}
    )
    assert resp.status_code == 401


def test_model_service_rejects_missing_features_with_422():
    """Model service rejects missing required features with HTTP 422 listing missing names."""
    client = TestClient(model_app)
    incomplete_features = {
        "on_call": True,
        "amount": 5000.0,
        "entry_channel": "typed_vpa"
    }
    resp = client.post(
        "/score",
        json={"features": incomplete_features, "note_intent": "none"},
        headers={"X-Internal-Key": "satark-internal-model-key-2026"}
    )
    assert resp.status_code == 422
    assert "Missing features" in resp.text


def test_http_model_client_contract(http_model_client, sample_features):
    """HttpModelClient successfully calls model service and parses contract."""
    res = http_model_client.score(sample_features, note_intent="food")
    assert "fusion_score" in res
    assert isinstance(res["fusion_score"], float)
    assert res.get("tier_hint") in ("green", "amber", "red")
    assert isinstance(res.get("reasons"), list)


# -----------------------------------------------------------------------------
# 2. Failure Tests: Service Down, Timeout, Wrong Key, Missing Feature
# -----------------------------------------------------------------------------

def test_failure_model_service_down_returns_amber_check_unavailable(test_db_path):
    """When model service is down/unreachable, API returns amber CHECK_UNAVAILABLE, never green."""
    # Unreachable port ensures connection error and retry
    dead_client = HttpModelClient(
        base_url="http://127.0.0.1:59999",
        api_key="satark-internal-model-key-2026",
        timeout_seconds=0.100
    )
    store = SQLiteFeatureStore(test_db_path)
    audit = AuditLogStore(test_db_path)
    policy = PolicyEngine(scorer=dead_client)

    risk_api_app.dependency_overrides[get_feature_store] = lambda: store
    risk_api_app.dependency_overrides[get_audit_store] = lambda: audit
    risk_api_app.dependency_overrides[get_policy_engine] = lambda: policy

    with TestClient(risk_api_app) as api_client:
        # Use an unseeded new payee to ensure the eligibility gate forwards to scorer
        payload = {
            "txn_ref": "t-down-01",
            "user_ref": "raksham@oksbi",
            "payee_vpa": "unknown-new-recipient@okaxis",
            "amount": 2500.0,
            "session": {"on_call": False}
        }
        resp = api_client.post("/v1/risk/assess", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "amber", "Model down must return amber fallback"
        assert data["tier"] != "green", "Must NEVER return green when model fails"
        assert "CHECK_UNAVAILABLE" in data["reasons"]
        assert data["hold_minutes"] == 0
        assert "fusion_score" not in data


def test_failure_model_service_timeout_returns_amber_check_unavailable(test_db_path):
    """When model service call times out, API returns amber CHECK_UNAVAILABLE, never green."""
    class TimingOutTransport(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Simulated inference timeout", request=request)

    mock_client = httpx.Client(transport=TimingOutTransport())
    timing_out_client = HttpModelClient(
        base_url="http://slow-model-service",
        api_key="satark-internal-model-key-2026",
        timeout_seconds=0.300,
        client=mock_client
    )

    store = SQLiteFeatureStore(test_db_path)
    audit = AuditLogStore(test_db_path)
    policy = PolicyEngine(scorer=timing_out_client)

    risk_api_app.dependency_overrides[get_feature_store] = lambda: store
    risk_api_app.dependency_overrides[get_audit_store] = lambda: audit
    risk_api_app.dependency_overrides[get_policy_engine] = lambda: policy

    with TestClient(risk_api_app) as api_client:
        payload = {
            "txn_ref": "t-timeout-01",
            "user_ref": "raksham@oksbi",
            "payee_vpa": "timeout-check-recipient@okaxis",
            "amount": 3500.0
        }
        resp = api_client.post("/v1/risk/assess", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "amber"
        assert data["tier"] != "green"
        assert "CHECK_UNAVAILABLE" in data["reasons"]


def test_failure_wrong_internal_key_returns_amber_check_unavailable(test_db_path):
    """When internal API key is rejected by model service, API returns amber CHECK_UNAVAILABLE."""
    test_client = TestClient(model_app)
    unauthorized_client = HttpModelClient(
        base_url="http://testserver",
        api_key="WRONG-INTERNAL-KEY-999",
        client=test_client
    )

    store = SQLiteFeatureStore(test_db_path)
    audit = AuditLogStore(test_db_path)
    policy = PolicyEngine(scorer=unauthorized_client)

    risk_api_app.dependency_overrides[get_feature_store] = lambda: store
    risk_api_app.dependency_overrides[get_audit_store] = lambda: audit
    risk_api_app.dependency_overrides[get_policy_engine] = lambda: policy

    with TestClient(risk_api_app) as api_client:
        payload = {
            "txn_ref": "t-key-01",
            "user_ref": "raksham@oksbi",
            "payee_vpa": "wrong-key-test-recipient@okaxis",
            "amount": 5000.0
        }
        resp = api_client.post("/v1/risk/assess", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "amber"
        assert data["tier"] != "green"
        assert "CHECK_UNAVAILABLE" in data["reasons"]


def test_failure_missing_feature_in_feature_builder_returns_amber(test_db_path):
    """If a required feature cannot be computed, API returns amber CHECK_UNAVAILABLE instead of 400."""
    store = SQLiteFeatureStore(test_db_path)
    audit = AuditLogStore(test_db_path)
    local_client = LocalModelClient()
    policy = PolicyEngine(scorer=local_client)

    risk_api_app.dependency_overrides[get_feature_store] = lambda: store
    risk_api_app.dependency_overrides[get_audit_store] = lambda: audit
    risk_api_app.dependency_overrides[get_policy_engine] = lambda: policy

    # Corrupt store method so it returns None for payee_age_days
    original_get_payee_profile = store.get_payee_profile
    def corrupt_get_payee_profile(vpa, **kwargs):  # accepts exclude_payer (new keyword)
        p = original_get_payee_profile(vpa, **kwargs)
        p["payee_age_days"] = None  # Missing feature from builder
        return p
    store.get_payee_profile = corrupt_get_payee_profile

    with TestClient(risk_api_app) as api_client:
        payload = {
            "txn_ref": "t-missing-feat-01",
            "user_ref": "raksham@oksbi",
            "payee_vpa": "new-payee-missing-feature@ybl",
            "amount": 1000.0
        }
        resp = api_client.post("/v1/risk/assess", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "amber"
        assert data["tier"] != "green"
        assert "CHECK_UNAVAILABLE" in data["reasons"]


# -----------------------------------------------------------------------------
# 3. Parity Test: LocalModelClient vs HttpModelClient
# -----------------------------------------------------------------------------

def test_parity_local_vs_http_model_client(sample_features, http_model_client):
    """LocalModelClient and HttpModelClient produce identical scores, tier hints, and reasons."""
    local_client = LocalModelClient()

    # Test Case A: Low risk payment
    local_res_a = local_client.score(sample_features, note_intent="food")
    http_res_a = http_model_client.score(sample_features, note_intent="food")

    assert np.isclose(local_res_a["fusion_score"], http_res_a["fusion_score"], atol=1e-5)
    assert local_res_a["tier_hint"] == http_res_a["tier_hint"]
    assert local_res_a["reasons"] == http_res_a["reasons"]

    # Test Case B: High risk coerced payment
    coerced_features = dict(sample_features)
    coerced_features.update({
        "on_call": True,
        "screen_shared": True,
        "payee_first_time": True,
        "payee_verified": False,
        "payee_age_days": 1.0,
        "amount": 65000.0,
        "amount_ratio": 15.0,
        "amount_z": 3.5,
        "payee_reports_prior": 4
    })
    local_res_b = local_client.score(coerced_features, note_intent="kyc")
    http_res_b = http_model_client.score(coerced_features, note_intent="kyc")

    assert np.isclose(local_res_b["fusion_score"], http_res_b["fusion_score"], atol=1e-5)
    assert local_res_b["tier_hint"] == http_res_b["tier_hint"]
    assert local_res_b["reasons"] == http_res_b["reasons"]


# -----------------------------------------------------------------------------
# 4. Latency Benchmark: 200+ Requests for Both Modes
# -----------------------------------------------------------------------------

def test_latency_benchmark_both_modes(sample_features, http_model_client):
    """
    Benchmarks 205 requests for:
    - Mode 1: LocalModelClient (in-process)
    - Mode 2: HttpModelClient (via HTTP TestClient)
    Verifies p95 < 150 ms in both modes and prints comparison.
    """
    local_client = LocalModelClient()
    total_runs = 205

    # 1. Benchmark LocalModelClient
    for _ in range(5):  # warmup
        local_client.score(sample_features, "food")

    local_latencies = []
    for _ in range(total_runs):
        t0 = time.perf_counter()
        local_client.score(sample_features, "food")
        local_latencies.append((time.perf_counter() - t0) * 1000.0)

    local_p50 = float(np.percentile(local_latencies, 50))
    local_p95 = float(np.percentile(local_latencies, 95))
    local_mean = float(np.mean(local_latencies))

    # 2. Benchmark HttpModelClient
    for _ in range(5):  # warmup
        http_model_client.score(sample_features, "food")

    http_latencies = []
    for _ in range(total_runs):
        t0 = time.perf_counter()
        http_model_client.score(sample_features, "food")
        http_latencies.append((time.perf_counter() - t0) * 1000.0)

    http_p50 = float(np.percentile(http_latencies, 50))
    http_p95 = float(np.percentile(http_latencies, 95))
    http_mean = float(np.mean(http_latencies))

    print("\n" + "="*60)
    print("      SATARK SCORING LATENCY BENCHMARK (205 REQUESTS)     ")
    print("="*60)
    print(f"Mode 1: LocalModelClient (In-Process)")
    print(f"  - Mean latency: {local_mean:.2f} ms")
    print(f"  - p50 latency:  {local_p50:.2f} ms")
    print(f"  - p95 latency:  {local_p95:.2f} ms (Target < 150 ms)")
    print("-"*60)
    print(f"Mode 2: HttpModelClient (HTTP Model Service)")
    print(f"  - Mean latency: {http_mean:.2f} ms")
    print(f"  - p50 latency:  {http_p50:.2f} ms")
    print(f"  - p95 latency:  {http_p95:.2f} ms (Target < 150 ms)")
    print("="*60)

    assert local_p95 < 150.0, f"LocalModelClient p95 exceeded 150ms: {local_p95:.2f} ms"
    assert http_p95 < 150.0, f"HttpModelClient p95 exceeded 150ms: {http_p95:.2f} ms"
