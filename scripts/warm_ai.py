from __future__ import annotations

import os
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.embedding_service import warm_embedding_model


def package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "missing"


print("ContextIQ AI runtime check")
print("-" * 48)
for package in [
    "sentence-transformers",
    "torch",
    "transformers",
    "scikit-learn",
    "google-genai",
]:
    print(f"{package:24} {package_version(package)}")

print(f"{'Gemini key configured':24} {'yes' if os.getenv('GEMINI_API_KEY', '').strip() else 'no'}")
print(f"{'Gemini model':24} {os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')}")
print(f"{'Thinking level':24} {os.getenv('GEMINI_THINKING_LEVEL', 'low')}")

print("\nWarming local semantic model...")
started = time.perf_counter()
model = warm_embedding_model()
elapsed = time.perf_counter() - started
print(f"Ready: {model} in {elapsed:.2f}s")
print("The first run may download model weights; later runs reuse the local Hugging Face cache.")
