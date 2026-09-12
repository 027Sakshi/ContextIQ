from google.oauth2.credentials import Credentials

from backend.app.services import google_token_store


def test_google_token_store_is_per_user_and_encrypted(tmp_path, monkeypatch):
    monkeypatch.setattr(google_token_store, "TOKEN_DIR", tmp_path)
    creds = Credentials(
        token="access-token",
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=["scope-a"],
    )
    google_token_store.save_google_credentials("person@example.com", creds)
    files = list(tmp_path.glob("*.token"))
    assert len(files) == 1
    assert b"refresh-token" not in files[0].read_bytes()
    loaded = google_token_store.load_google_credentials("person@example.com", scopes=["scope-a"])
    assert loaded is not None
    assert loaded.refresh_token == "refresh-token"
