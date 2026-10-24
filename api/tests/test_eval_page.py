"""Results page: serves the last logged holdout run and refuses fixed seeds for fresh worlds."""
from fastapi.testclient import TestClient

from api.main import app


def test_latest_holdout_run_and_notes(client: TestClient):
    d = client.get("/v1/eval/latest").json()
    assert d["runs_logged"] >= 1 and d["result"]["role"] == "holdout"
    assert d["result"]["holdout_run"] == d["runs_logged"]  # the page always shows the last run
    assert "failure" in d["failure_notes"].lower() or "missed" in d["failure_notes"].lower()


def test_fresh_world_refuses_train_validation_and_holdout_seeds(client: TestClient):
    for seed in (11, 22, 33):
        assert client.post("/v1/eval/fresh", json={"seed": seed}).status_code == 409
    assert client.get("/eval").status_code == 200


def test_fresh_world_needs_the_analyst_key(client: TestClient):
    with TestClient(app) as anon:
        assert anon.post("/v1/eval/fresh", json={"seed": 4711}).status_code == 401
