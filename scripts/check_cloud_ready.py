from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

print("ContextIQ Streamlit Cloud readiness")
print("-" * 48)

required_files = [
    "streamlit_app.py",
    "requirements.txt",
    ".streamlit/config.toml",
    "frontend/app.py",
    "backend/app/main.py",
]

ok = True

for rel in required_files:
    exists = (ROOT / rel).exists()
    print(f"{rel:<32} {'OK' if exists else 'MISSING'}")
    ok = ok and exists

print()

for module in ["streamlit", "uvicorn", "google.genai", "sentence_transformers"]:
    found = importlib.util.find_spec(module) is not None
    print(f"{module:<32} {'OK' if found else 'MISSING'}")
    ok = ok and found

requirements = (ROOT / "requirements.txt").read_text(
    encoding="utf-8",
    errors="ignore",
).lower()

if "openai==" in requirements:
    print()
    print("ERROR: legacy OpenAI dependency is still present.")
    ok = False

print()
print("Local/deployment configuration (values hidden)")

for key in [
    "GEMINI_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_OAUTH_REDIRECT_URI",
    "CONTEXTIQ_SESSION_SECRET",
]:
    state = "SET" if os.getenv(key, "").strip() else "NOT SET"
    print(f"{key:<32} {state}")

redirect = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip()

if redirect:
    if redirect.startswith("https://"):
        print("Google OAuth redirect             HTTPS")
    else:
        print("Google OAuth redirect             LOCAL/NOT CLOUD")
else:
    print("Google OAuth redirect             NOT SET")

print()

if ok:
    print("PASS: code/dependencies are ready for Streamlit Community Cloud.")
    print("Deployment secrets belong in Streamlit Cloud settings, not Git.")
else:
    raise SystemExit("FAIL: resolve the items above before deploying.")
