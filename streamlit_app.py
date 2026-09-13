from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

SUPPORTED_SECRET_KEYS = (
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_THINKING_LEVEL",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_OAUTH_REDIRECT_URI",
    "CONTEXTIQ_SESSION_SECRET",
    "DATABASE_URL",
    "ALLOW_DEV_EMAIL_LOGIN",
    "ALLOW_DIRECT_EMAIL_LOGIN",
    "CONTEXTIQ_DIRECT_LOGIN_CODE",
    "HF_TOKEN",
)


def _bridge_streamlit_secrets() -> None:
    try:
        available = set(st.secrets.keys())
    except Exception:
        available = set()

    for key in SUPPORTED_SECRET_KEYS:
        if key not in available:
            continue
        try:
            value = st.secrets[key]
        except Exception:
            continue
        if value is None:
            continue
        text = str(value).strip()
        if text:
            os.environ[key] = text


_bridge_streamlit_secrets()

os.environ.setdefault("CONTEXTIQ_API_URL", "http://127.0.0.1:8000")
os.environ.setdefault("GEMINI_MODEL", "gemini-3.8-flash")
os.environ.setdefault("GEMINI_THINKING_LEVEL", "low")
os.environ.setdefault("ALLOW_DEV_EMAIL_LOGIN", "false")
os.environ.setdefault("ALLOW_DIRECT_EMAIL_LOGIN", "true")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

(ROOT / "data").mkdir(parents=True, exist_ok=True)


def _port_is_open(host: str = "127.0.0.1", port: int = 8000) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


@st.cache_resource(show_spinner=False)
def _start_contextiq_api():
    if _port_is_open():
        return "existing"

    import uvicorn

    def _serve() -> None:
        config = uvicorn.Config(
            "backend.app.main:app",
            host="127.0.0.1",
            port=8000,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        server.run()

    thread = threading.Thread(
        target=_serve,
        name="contextiq-fastapi",
        daemon=True,
    )
    thread.start()

    deadline = time.time() + 20
    while time.time() < deadline:
        if _port_is_open():
            return thread
        if not thread.is_alive():
            break
        time.sleep(0.15)

    raise RuntimeError(
        "ContextIQ API failed to start on 127.0.0.1:8000. "
        "Check the Streamlit Cloud logs for the backend startup error."
    )


_start_contextiq_api()

import frontend.app  # noqa: E402,F401
