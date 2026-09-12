from backend.app.services import gmail_action_service


class _Execute:
    def __init__(self, value): self.value = value
    def execute(self): return self.value


class _Drafts:
    def create(self, **kwargs):
        assert kwargs["userId"] == "me"
        assert kwargs["body"]["message"]["raw"]
        return _Execute({"id": "draft-1", "message": {"id": "msg-1"}})


class _Users:
    def drafts(self): return _Drafts()


class _Service:
    def users(self): return _Users()


def test_create_gmail_draft_never_sends(monkeypatch):
    monkeypatch.setattr(gmail_action_service, "get_gmail_service", lambda: _Service())
    result = gmail_action_service.create_gmail_draft("Client <client@example.com>", "Re: Hello", "Draft body")
    assert result["draft_id"] == "draft-1"
    assert result["recipient"] == "client@example.com"
