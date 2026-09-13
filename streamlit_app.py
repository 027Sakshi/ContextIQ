from __future__ import annotations

import os
import subprocess
import sys
import atexit
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
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

(ROOT / "data").mkdir(parents=True, exist_ok=True)


def _port_is_open(host: str = "127.0.0.1", port: int = 8000) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


@st.cache_resource(show_spinner=False)
def _start_contextiq_api():
    """
    Start FastAPI as an internal child process.

    This is more reliable than running Uvicorn inside Streamlit's
    event-loop process/thread and works both locally and on
    Streamlit Community Cloud.
    """

    # Another rerun/process may already have started it.
    if _port_is_open():
        print("[ContextIQ] API already available on 127.0.0.1:8000")
        return None

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--log-level",
        "warning",
        "--no-access-log",
    ]

    print("[ContextIQ] Starting internal FastAPI service...")

    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        env=os.environ.copy(),
    )

    def _cleanup_api():
        try:
            if process.poll() is None:
                process.terminate()
        except Exception:
            pass

    atexit.register(_cleanup_api)

    # Cloud cold starts can be slower than local starts.
    deadline = time.time() + 60

    while time.time() < deadline:
        if _port_is_open():
            print(
                "[ContextIQ] FastAPI ready at "
                "http://127.0.0.1:8000"
            )
            return process

        exit_code = process.poll()

        if exit_code is not None:
            raise RuntimeError(
                "ContextIQ FastAPI exited during startup "
                f"with code {exit_code}. "
                "See the terminal/cloud logs immediately above "
                "for the real backend error."
            )

        time.sleep(0.25)

    try:
        process.terminate()
    except Exception:
        pass

    raise RuntimeError(
        "ContextIQ FastAPI did not become ready within "
        "60 seconds."
    )


_start_contextiq_api()


@st.cache_resource(show_spinner=False)
def _start_ai_warmup():
    """
    Warm ContextIQ's semantic model in the same Python process used by
    Streamlit + FastAPI. This avoids making the user's first Ask ContextIQ
    request pay the full SentenceTransformer model-load cost.
    """
    def _warm():
        try:
            from backend.app.services.embedding_service import hybrid_scores

            hybrid_scores(
                "ContextIQ semantic warmup",
                [
                    "business email customer contract calendar "
                    "commitment opportunity context"
                ],
            )

            print("[ContextIQ] Semantic retrieval model ready.")

        except Exception as exc:
            # Retrieval already has lexical/fallback behavior, so semantic
            # warmup failure must never prevent the UI from starting.
            print(
                "[ContextIQ] Semantic warmup deferred:",
                type(exc).__name__,
                str(exc),
            )

    worker = threading.Thread(
        target=_warm,
        name="contextiq-semantic-warmup",
        daemon=True,
    )
    worker.start()
    return worker


_start_ai_warmup()

import runpy

# IMPORTANT:
# Streamlit reruns this entrypoint after every widget interaction.
# A normal "import frontend.app" only executes once because Python caches
# imported modules, which caused Analyze / Refresh / navigation to render
# a blank page after the first interaction.
#
# runpy executes the actual UI again on every Streamlit rerun.
runpy.run_module("frontend.app", run_name="__main__")
