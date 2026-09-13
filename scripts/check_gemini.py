from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

api_key = os.getenv("GEMINI_API_KEY", "").strip()
model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
timeout_seconds = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "18"))
thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "low").strip().lower() or "low"

if not api_key:
    raise SystemExit("ERROR: GEMINI_API_KEY is not configured in .env")

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(timeout=max(1, int(timeout_seconds * 1000))),
)

try:
    interaction = client.interactions.create(
        model=model,
        input="Reply with exactly CONTEXTIQ_GEMINI_OK",
        system_instruction="Follow the user's output-format instruction exactly.",
        generation_config={
            "thinking_level": thinking_level,
            "max_output_tokens": 64,
        },
        store=False,
    )
except Exception as error:
    print(f"ERROR: Gemini request failed: {type(error).__name__}: {error}")
    raise SystemExit(1) from error

text = str(getattr(interaction, "output_text", "") or "").strip()
print("Model:", model)
print("Native SDK: google-genai")
print("Interactions API: OK")
print("Response:", text or "<empty>")

if "CONTEXTIQ_GEMINI_OK" not in text:
    raise SystemExit("ERROR: Gemini returned an unexpected or empty response")

print("PASS: native Gemini runtime is ready")
