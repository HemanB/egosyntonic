"""End-to-end fixture-mode pipeline smoke test.

Asserts the full extraction → retrieval → reasoning → generation → critic
pipeline runs without error in fixture mode and returns a structured plan.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_turn_runs_full_pipeline(client: TestClient) -> None:
    payload = {
        "user_id": "ignored-overridden-by-auth",
        "session_id": "test-session-1",
        "utterance_text": "I'm not sure how I feel about today.",
    }
    response = client.post("/turn", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()

    # Auth bypass user wins over client-supplied user_id
    assert body["plan"]["receptivity"]["score"] == 0.3
    assert body["plan"]["orchestration"]["intervention_intensity"] == "presence"
    assert body["critic"]["passed"] is True
    assert body["used_safety_template"] is False
    assert body["regeneration_attempts"] == 0
    assert isinstance(body["latency_ms"], int)
    assert body["response_text"]


def test_turn_requires_session_id(client: TestClient) -> None:
    response = client.post("/turn", json={"user_id": "x", "utterance_text": "hi"})
    assert response.status_code == 422
