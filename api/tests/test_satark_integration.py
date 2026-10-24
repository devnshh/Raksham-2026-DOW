"""
Integration tests for Satark fusion model inside FastAPI risk service.
Tests real endpoint for GREEN/RED journeys, missing feature validation, and p95 latency.
"""

import time
import numpy as np
import pytest
from fastapi.testclient import TestClient


def test_real_endpoint_green_payment_known_verified_payee(client: TestClient):
    """
    Task 7a: Green payment through real endpoint.
    Small payment (₹220) to known verified merchant (swiggy@axisbank).
    Strict contract: returns tier='green', hold_minutes=0, reasons=[], no internal scores.
    """
    payload = {
        "txn_ref": "txn_test_green_001",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "swiggy@axisbank",
        "amount": 220.0,
        "entry_channel": "typed_vpa",
        "session": {
            "on_call": False,
            "screen_shared": False,
            "remote_app_present": False,
            "remote_app_new": False,
            "app_switches": 0,
            "typing_ms": 260.0,
            "pauses": 0,
            "pin_secs": 2.9,
            "device_new": False,
            "failed_auth": 0
        },
        "context": {
            "note_intent": "food",
            "note_text": "dinner delivery"
        }
    }

    resp = client.post("/v1/risk/assess", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # Exact contract assertions
    assert data["tier"] == "green"
    assert data["hold_minutes"] == 0
    assert data["reasons"] == [], "Green tier must never include reasons"
    assert data["template_id"] in ["green_silent_pass", "green_pass_v1"]
    assert "case_id" in data
    assert data["case_id"].startswith("c-")

    # Strict privacy assertions: NEVER expose model internals or fusion scores
    assert "fusion_score" not in data
    assert "score" not in data
    assert "model_weights" not in data
    assert "family_contrib" not in data
    assert "feature_vector" not in data


def test_real_endpoint_red_payment_first_time_unverified_coerced(client: TestClient):
    """
    Task 7a: Red payment through real endpoint.
    First-time unverified payee, large amount (₹65,000), on_call=True and screen_shared=True.
    Corroboration rule fires: Family A (on_call, screen_shared) + Family B/D.
    Strict contract: tier='red', hold_minutes=30, template_id, reasons present.
    """
    payload = {
        "txn_ref": "txn_test_red_001",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "unverified-cyber-officer@okaxis",
        "amount": 65000.0,
        "entry_channel": "typed_vpa",
        "session": {
            "on_call": True,
            "screen_shared": True,
            "remote_app_present": False,
            "remote_app_new": False,
            "app_switches": 4,
            "typing_ms": 490.0,
            "pauses": 4,
            "pin_secs": 9.5,
            "device_new": False,
            "failed_auth": 0
        },
        "context": {
            "note_intent": "kyc",
            "note_text": "cbi clearance fee"
        }
    }

    resp = client.post("/v1/risk/assess", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data["tier"] == "red"
    assert data["hold_minutes"] == 30
    assert len(data["reasons"]) > 0
    assert "ON_CALL" in data["reasons"] or "SCREEN_SHARED" in data["reasons"]
    assert data["template_id"] in ["red_call_new_payee_v1", "red_coached_intervention_v1"]
    assert "case_id" in data

    # Strict privacy assertions: NEVER expose model internals
    assert "fusion_score" not in data
    assert "score" not in data
    assert "model_weights" not in data


def test_real_endpoint_missing_required_feature_no_silent_default(client: TestClient):
    """
    Task 7b: Request with a missing required feature returns a clear error, never a silent default.
    Missing non-optional request field returns 422 or 400 error and never passes silently as green.
    """
    # 1. Missing payee_vpa completely
    malformed_payload_1 = {
        "amount": 5000.0,
        "session": {"on_call": True}
    }
    resp1 = client.post("/v1/risk/assess", json=malformed_payload_1)
    assert resp1.status_code in [400, 422], "Missing required payee_vpa must return 400 or 422 error"
    assert resp1.json().get("tier") != "green", "Missing required feature must NEVER silently default to green"

    # 2. Missing amount
    malformed_payload_2 = {
        "payee_vpa": "unknown-payee@ybl",
        "session": {"on_call": False}
    }
    resp2 = client.post("/v1/risk/assess", json=malformed_payload_2)
    assert resp2.status_code in [400, 422], "Missing amount must return 400 or 422 error"
    assert resp2.json().get("tier") != "green", "Missing required feature must NEVER silently default to green"


def test_real_endpoint_latency_200_requests(client: TestClient):
    """
    Task 7c: Latency test with 200+ requests through real endpoint.
    Target p95 latency under 150 ms.
    """
    payload = {
        "txn_ref": "txn_latency_bench",
        "user_ref": "raksham@oksbi",
        "payee_vpa": "zomato@hdfcbank",
        "amount": 350.0,
        "entry_channel": "typed_vpa",
        "session": {
            "on_call": False,
            "screen_shared": False,
            "remote_app_present": False,
            "remote_app_new": False,
            "app_switches": 0,
            "typing_ms": 280.0,
            "pauses": 0,
            "pin_secs": 3.0,
            "device_new": False,
            "failed_auth": 0
        },
        "context": {
            "note_intent": "food",
            "note_text": "lunch order"
        }
    }

    # Warmup 5 requests
    for _ in range(5):
        client.post("/v1/risk/assess", json=payload)

    # 205 benchmark requests
    durations_ms = []
    total_requests = 205

    for _ in range(total_requests):
        t0 = time.perf_counter()
        resp = client.post("/v1/risk/assess", json=payload)
        t_elapsed = (time.perf_counter() - t0) * 1000.0
        assert resp.status_code == 200
        durations_ms.append(t_elapsed)

    p50 = float(np.percentile(durations_ms, 50))
    p95 = float(np.percentile(durations_ms, 95))
    p99 = float(np.percentile(durations_ms, 99))
    mean_val = float(np.mean(durations_ms))

    print(f"\n[LATENCY REPORT: 205 REQUESTS]")
    print(f"  Mean latency: {mean_val:.2f} ms")
    print(f"  p50 latency:  {p50:.2f} ms")
    print(f"  p95 latency:  {p95:.2f} ms (Target < 150 ms)")
    print(f"  p99 latency:  {p99:.2f} ms")

    assert p95 < 150.0, f"p95 latency was {p95:.2f} ms, expected < 150.0 ms"
