from fastapi.testclient import TestClient

from backend.app.auth_session import create_session_token
from backend.app.main import app


def test_assistant_requires_user():
    response = TestClient(app).post("/assistant/ask", json={"question": "What matters today?"})
    assert response.status_code == 401


def test_assistant_accepts_signed_session(monkeypatch):
    monkeypatch.setattr(
        "backend.app.routes.assistant.retrieve_business_knowledge",
        lambda db, user, query, top_k: {
            "retrieval_model": "test",
            "document_count": 1,
            "evidence": [{"evidence_id": "E1", "source_type": "email", "source_id": 1, "title": "Renewal", "score": .9, "excerpt": "Renewal due tomorrow", "metadata": {}}],
        },
    )
    monkeypatch.setattr(
        "backend.app.routes.assistant.answer_business_question",
        lambda question, evidence: {"answer": "Act on the renewal [E1]", "confidence": .9, "provider": "test", "used_evidence": ["E1"], "recommended_next_steps": []},
    )
    token = create_session_token("user@example.com", "User")
    response = TestClient(app).post(
        "/assistant/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "What matters today?"},
    )
    assert response.status_code == 200
    assert response.json()["used_evidence"] == ["E1"]
