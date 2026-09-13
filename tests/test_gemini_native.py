from types import SimpleNamespace

from backend.app.services import llm_service


class FakeInteractions:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text: str):
        self.interactions = FakeInteractions(output_text)


def test_reply_draft_uses_native_interactions_api(monkeypatch):
    fake = FakeClient(
        '{"subject":"Re: Renewal","body":"Thanks for the update.","confidence":0.88}'
    )
    monkeypatch.setattr(llm_service, "_get_client", lambda: fake)

    result = llm_service.generate_reply_draft(
        {"subject": "Renewal", "sender": "a@example.com", "body": "Please confirm."},
        [],
    )

    assert result["provider"] == "gemini"
    assert result["subject"] == "Re: Renewal"
    assert result["confidence"] == 0.88
    assert len(fake.interactions.calls) == 1
    call = fake.interactions.calls[0]
    assert call["model"] == llm_service.GEMINI_MODEL
    assert call["store"] is False
    assert call["generation_config"]["thinking_level"] in {"low", "medium", "high"}
    assert call["response_format"]["mime_type"] == "application/json"


def test_project_no_longer_depends_on_openai_client():
    requirements = (llm_service.PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    source = (llm_service.PROJECT_ROOT / "backend/app/services/llm_service.py").read_text(encoding="utf-8").lower()

    assert "openai==" not in requirements
    assert "from openai" not in source
    assert "import openai" not in source
    assert "google-genai" in requirements
