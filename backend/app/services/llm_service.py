import json
import os
from typing import Any

from openai import OpenAI


# ==========================================================
# CONFIGURATION
# ==========================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
).strip()

GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai/"
)


# ==========================================================
# CLIENT
# ==========================================================

def _get_client() -> OpenAI | None:
    """
    Create an OpenAI-compatible client that sends requests
    to Google's Gemini API.

    The Gemini API key is read from GEMINI_API_KEY.
    """
    if not GEMINI_API_KEY:
        return None

    return OpenAI(
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL,
    )


# ==========================================================
# HELPERS
# ==========================================================

def _safe_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
    except Exception:
        return str(value)


def _extract_json(text: str) -> dict:
    """
    Convert a model response into a dictionary.

    Handles:
    1. Normal JSON
    2. JSON wrapped in ```json ... ```
    3. JSON embedded in surrounding text
    """
    if not text:
        return {}

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace(
            "```json",
            "",
            1,
        )
        cleaned = cleaned.replace(
            "```",
            "",
        ).strip()

    try:
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start:end + 1]

        try:
            parsed = json.loads(candidate)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

    return {}


def _fallback_insight(
    email: dict,
    analysis: dict,
    rag_context: str,
) -> dict:
    """
    Safe local fallback when Gemini is unavailable.
    """
    decision = analysis.get(
        "decision",
        {},
    )

    consequence = analysis.get(
        "consequence",
        {},
    )

    context = analysis.get(
        "business_context",
        analysis.get(
            "context",
            {},
        ),
    )

    intent = analysis.get(
        "intent",
        "unknown",
    )

    priority = analysis.get(
        "priority_score",
        analysis.get(
            "priority",
            0,
        ),
    )

    sender_trust = analysis.get(
        "sender_trust",
        0,
    )

    impact_score = consequence.get(
        "score",
        0,
    )

    action_type = decision.get(
        "action_type",
        "categorize_and_monitor",
    )

    company = None

    if isinstance(context, dict):
        company_data = context.get(
            "company"
        )

        if isinstance(company_data, dict):
            company = company_data.get(
                "name"
            )

    business_meaning = (
        f"This email was classified as "
        f"{str(intent).replace('_', ' ').title()}."
    )

    if company:
        business_meaning += (
            f" The message is associated with "
            f"{company}."
        )

    historical_context = (
        "Historical communication was retrieved "
        "from the local RAG pipeline."
        if rag_context
        else
        "No additional historical context was retrieved."
    )

    business_impact = (
        f"Business impact score: {impact_score}/100."
    )

    if consequence.get(
        "potential_revenue_at_risk"
    ):
        business_impact += (
            " Potential revenue at risk: "
            f"{consequence['potential_revenue_at_risk']}."
        )

    recommended_action = (
        str(action_type)
        .replace("_", " ")
        .title()
    )

    confidence = (
        decision.get(
            "confidence",
            0.75,
        )
    )

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.75

    return {
        "provider": "fallback",
        "model": "local-fallback",
        "message": (
            f"Business Meaning: {business_meaning}\n\n"
            f"Historical Context: {historical_context}\n\n"
            f"Business Impact: {business_impact}\n\n"
            f"Recommended Action: {recommended_action}\n\n"
            f"Priority: {priority}/100\n"
            f"Sender Trust: {float(sender_trust) * 100:.0f}%\n"
            f"Confidence: {confidence * 100:.0f}%"
        ),
        "business_meaning": business_meaning,
        "historical_context": historical_context,
        "business_impact": business_impact,
        "recommended_action": recommended_action,
        "confidence": confidence,
        "retrieved_count": 0,
    }


# ==========================================================
# GEMINI BUSINESS INSIGHT
# ==========================================================

def generate_business_insight(
    email: dict,
    analysis: dict,
    rag_context: str = "",
) -> dict:
    """
    Generate ContextIQ's higher-level business insight using
    Gemini through Google's OpenAI-compatible endpoint.

    Expected inputs:
        email        -> current email
        analysis     -> AI/threat/context/consequence/decision
        rag_context  -> related historical email context

    Returns a dictionary used directly by the Streamlit UI.
    """

    fallback = _fallback_insight(
        email=email,
        analysis=analysis,
        rag_context=rag_context,
    )

    client = _get_client()

    if client is None:
        return fallback

    subject = _safe_text(
        email.get(
            "subject",
            "",
        )
    )

    sender = _safe_text(
        email.get(
            "sender",
            "",
        )
    )

    body = _safe_text(
        email.get(
            "body",
            "",
        )
    )

    analysis_text = _safe_text(
        analysis
    )

    rag_text = _safe_text(
        rag_context
    )

    prompt = f"""
You are ContextIQ, an AI business email intelligence system.

Your job is NOT to merely summarize an email.
You must explain what the email means for the business.

Analyze the email using:
- current email content
- AI intent
- priority
- sender trust
- business context
- consequence analysis
- process dependency
- decision/action
- historical RAG context

CURRENT EMAIL
--------------
Subject:
{subject}

Sender:
{sender}

Body:
{body}

CONTEXTIQ ANALYSIS
------------------
{analysis_text}

HISTORICAL RAG CONTEXT
----------------------
{rag_text}

Return ONLY valid JSON with exactly these keys:

{{
  "business_meaning": "...",
  "historical_context": "...",
  "business_impact": "...",
  "recommended_action": "...",
  "confidence": 0.0,
  "message": "..."
}}

Rules:
- confidence must be a number from 0.0 to 1.0.
- Do not invent facts that are not present in the email or supplied context.
- Mention business value/deadlines only when supported by the supplied context.
- Keep the message concise but useful for an executive dashboard.
- "message" should combine the five important outputs in readable prose.
"""

    try:
        response = client.chat.completions.create(
            model=GEMINI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful business intelligence "
                        "assistant. Output valid JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.2,
            max_tokens=900,
        )

        content = (
            response.choices[0].message.content
            if response.choices
            else ""
        )

        parsed = _extract_json(
            content
        )

        if not parsed:
            # Gemini may occasionally return plain text.
            # Keep that response rather than losing the insight.
            plain_text = (
                str(content).strip()
                if content
                else ""
            )

            if plain_text:
                return {
                    "provider": "gemini",
                    "model": GEMINI_MODEL,
                    "message": plain_text,
                    "business_meaning": plain_text,
                    "historical_context": "",
                    "business_impact": "",
                    "recommended_action": "",
                    "confidence": 0.85,
                    "retrieved_count": 0,
                }

            return fallback

        confidence = parsed.get(
            "confidence",
            0.85,
        )

        try:
            confidence = float(
                confidence
            )
        except (TypeError, ValueError):
            confidence = 0.85

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        business_meaning = str(
            parsed.get(
                "business_meaning",
                "",
            )
        ).strip()

        historical_context = str(
            parsed.get(
                "historical_context",
                "",
            )
        ).strip()

        business_impact = str(
            parsed.get(
                "business_impact",
                "",
            )
        ).strip()

        recommended_action = str(
            parsed.get(
                "recommended_action",
                "",
            )
        ).strip()

        message = str(
            parsed.get(
                "message",
                "",
            )
        ).strip()

        if not message:
            message = (
                f"Business Meaning: {business_meaning}\n\n"
                f"Historical Context: {historical_context}\n\n"
                f"Business Impact: {business_impact}\n\n"
                f"Recommended Action: {recommended_action}\n\n"
                f"Confidence: {confidence * 100:.0f}%"
            )

        return {
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "message": message,
            "business_meaning": business_meaning,
            "historical_context": historical_context,
            "business_impact": business_impact,
            "recommended_action": recommended_action,
            "confidence": confidence,
            "retrieved_count": 0,
        }

    except Exception:
        # Do not break the ContextIQ analysis pipeline if
        # Gemini is unavailable, rate-limited, or returns an error.
        return fallback
