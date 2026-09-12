import numpy as np

from backend.app.services import embedding_service
from backend.app.services.rag_service import retrieve_related_emails


def test_rag_ranks_business_related_email(monkeypatch):
    def fake_scores(query, documents):
        assert "renewal" in query.lower()
        return np.array([0.91, 0.12]), "test-model"

    monkeypatch.setattr(embedding_service, "hybrid_scores", fake_scores)
    # rag_service imported the function directly, patch there too.
    monkeypatch.setattr("backend.app.services.rag_service.hybrid_scores", fake_scores)

    current = {"id": 1, "subject": "Annual renewal", "sender": "a@x.com", "body": "renewal due"}
    emails = [
        current,
        {"id": 2, "subject": "Contract extension", "sender": "a@x.com", "body": "agreement expires soon"},
        {"id": 3, "subject": "Office lunch", "sender": "b@x.com", "body": "menu"},
    ]
    results = retrieve_related_emails(current, emails, top_k=1)
    assert results[0]["id"] == 2
    assert results[0]["retrieval_model"] == "test-model"
