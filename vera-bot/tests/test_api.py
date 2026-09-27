"""Test FastAPI HTTP endpoints."""
from __future__ import annotations
import pytest
from starlette.testclient import TestClient

from bot import app
from vera.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_store():
    store.reset()
    yield
    store.reset()


def test_healthz():
    resp = client.get("/v1/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert "contexts_loaded" in data


def test_metadata():
    resp = client.get("/v1/metadata")
    assert resp.status_code == 200
    data = resp.json()
    assert "team_name" in data
    assert "model" in data
    assert "approach" in data
    assert "version" in data


def test_context_push_and_stale_handling():
    # Push category
    payload = {"slug": "dentists", "voice": {"tone": "clinical"}}
    resp1 = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": payload,
    })
    assert resp1.status_code == 200
    assert resp1.json()["accepted"] is True

    # Push higher version
    resp2 = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "dentists",
        "version": 2,
        "payload": payload,
    })
    assert resp2.status_code == 200
    assert resp2.json()["accepted"] is True

    # Push lower (stale) version
    resp3 = client.post("/v1/context", json={
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": payload,
    })
    assert resp3.status_code == 200
    assert resp3.json()["accepted"] is False
    assert resp3.json()["reason"] == "stale_version"


def test_tick_and_reply_flow():
    # Setup context: category, merchant, trigger
    cat = {"slug": "dentists", "voice": {"tone": "clinical", "vocab_taboo": []}}
    merch = {
        "merchant_id": "m_test_1",
        "category_slug": "dentists",
        "identity": {"name": "Meera Dental", "owner_first_name": "Meera"},
        "performance": {"views": 1000, "calls": 20, "ctr": 0.05},
        "offers": [{"title": "Dental Cleaning @ ₹299", "status": "active"}],
    }
    trig = {
        "id": "trg_test_1",
        "kind": "perf_spike",
        "merchant_id": "m_test_1",
        "urgency": "medium",
        "payload": {"metric": "calls", "delta_pct": 0.15},
    }

    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat})
    client.post("/v1/context", json={"scope": "merchant", "context_id": "m_test_1", "version": 1, "payload": merch})
    client.post("/v1/context", json={"scope": "trigger", "context_id": "trg_test_1", "version": 1, "payload": trig})

    # Call tick
    tick_resp = client.post("/v1/tick", json={"now": "2026-04-26T10:00:00Z", "available_triggers": ["trg_test_1"]})
    assert tick_resp.status_code == 200
    actions = tick_resp.json().get("actions", [])
    assert len(actions) == 1
    action = actions[0]
    cid = action["conversation_id"]
    assert cid.startswith("conv_")
    assert action["merchant_id"] == "m_test_1"
    assert action["cta"] in ("open_ended", "binary_yes_no")
    assert "body" in action and len(action["body"]) > 0

    # Call reply with commit
    reply_resp = client.post("/v1/reply", json={
        "conversation_id": cid,
        "merchant_id": "m_test_1",
        "message": "Ok lets do it. Whats next?",
    })
    assert reply_resp.status_code == 200
    reply_data = reply_resp.json()
    assert reply_data["action"] == "send"
    assert "confirm" in reply_data["body"].lower() or "draft" in reply_data["body"].lower()


def test_teardown():
    client.post("/v1/context", json={
        "scope": "category",
        "context_id": "dentists",
        "version": 1,
        "payload": {"slug": "dentists"},
    })
    assert store.contexts.get("category", "dentists") is not None
    td = client.post("/v1/teardown")
    assert td.status_code == 200
    assert store.contexts.get("category", "dentists") is None
