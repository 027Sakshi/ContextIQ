import json
import os
from typing import Any
from pathlib import Path

from dotenv import load_dotenv

from openai import OpenAI


# ==========================================================
# CONFIGURATION
# ==========================================================

# Load ContextIQ's project-local environment before module-level LLM
# configuration is evaluated. This makes the service independent of
# import order and works consistently from Streamlit, Uvicorn and scripts.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash",
).strip()

GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai/"
)

GEMINI_TIMEOUT_SECONDS = float(
    os.getenv("GEMINI_TIMEOUT_SECONDS", "18")
)

GEMINI_MAX_RETRIES = int(
    os.getenv("GEMINI_MAX_RETRIES", "0")
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
        timeout=GEMINI_TIMEOUT_SECONDS,
        max_retries=GEMINI_MAX_RETRIES,
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
            max_tokens=650,
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

# ==========================================================
# ASK CONTEXTIQ — EVIDENCE-GROUNDED BUSINESS Q&A
# ==========================================================

def answer_business_question(question: str, evidence: list[dict]) -> dict:
    """Answer a business question using only retrieved ContextIQ evidence."""
    if not evidence:
        return {
            "provider": "local-fallback",
            "answer": "I do not have enough connected business evidence to answer that yet. Sync Gmail, add CRM context, or connect Calendar and try again.",
            "confidence": 0.0,
            "used_evidence": [],
            "recommended_next_steps": ["Connect or sync more business context."],
        }

    evidence_text = "\n\n".join(
        f"[{item['evidence_id']}] {item['source_type'].upper()} — {item['title']}\n{item['excerpt']}"
        for item in evidence
    )

    client = _get_client()
    if client is None:
        top = evidence[:3]
        summary = "\n".join(
            f"• [{item['evidence_id']}] {item['title']}: {item['excerpt'][:220]}"
            for item in top
        )
        return {
            "provider": "local-fallback",
            "answer": f"Most relevant evidence for your question:\n{summary}",
            "confidence": min(0.75, 0.35 + (0.1 * len(top))),
            "used_evidence": [item["evidence_id"] for item in top],
            "recommended_next_steps": [],
        }

    prompt = f"""
You are ContextIQ, an evidence-grounded business decision copilot.

QUESTION
{question}

RETRIEVED EVIDENCE
{evidence_text}

Return ONLY valid JSON:
{{
  "answer": "clear executive-quality answer with inline evidence references like [E1]",
  "confidence": 0.0,
  "used_evidence": ["E1"],
  "recommended_next_steps": ["specific next step"]
}}

Rules:
- Use ONLY the supplied evidence. Never invent a customer, amount, deadline, meeting, commitment, or risk.
- If evidence is insufficient, say exactly what is missing.
- Prefer specific business implications over generic email summaries.
- Cite factual claims with [E#] references.
- Keep the answer concise and decision-oriented.
"""

    try:
        response = client.chat.completions.create(
            model=GEMINI_MODEL,
            messages=[
                {"role": "system", "content": "Answer only from supplied business evidence. Output valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=750,
        )
        content = response.choices[0].message.content if response.choices else ""
        parsed = _extract_json(content)
        if not parsed:
            raise ValueError("Model did not return structured JSON")
        used = [str(item) for item in (parsed.get("used_evidence") or [])]
        valid_ids = {item["evidence_id"] for item in evidence}
        used = [item for item in used if item in valid_ids]
        confidence = float(parsed.get("confidence", 0.75))
        return {
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "answer": str(parsed.get("answer") or "").strip(),
            "confidence": max(0.0, min(1.0, confidence)),
            "used_evidence": used,
            "recommended_next_steps": [str(item) for item in (parsed.get("recommended_next_steps") or [])][:5],
        }
    except Exception:
        top = evidence[:3]
        return {
            "provider": "local-fallback",
            "answer": "\n".join(f"• [{item['evidence_id']}] {item['title']}: {item['excerpt'][:220]}" for item in top),
            "confidence": 0.5,
            "used_evidence": [item["evidence_id"] for item in top],
            "recommended_next_steps": [],
        }

# ==========================================================
# HUMAN-APPROVED REPLY DRAFTS
# ==========================================================

def generate_reply_draft(email: dict, evidence: list[dict]) -> dict:
    subject = str(email.get("subject") or "").strip()
    sender = str(email.get("sender") or "").strip()
    body = str(email.get("body") or "").strip()
    evidence_text = "\n\n".join(
        f"[{item['evidence_id']}] {item['source_type']}: {item['title']}\n{item['excerpt']}"
        for item in evidence[:8]
    )
    fallback = {
        "subject": subject if subject.lower().startswith("re:") else f"Re: {subject}",
        "body": (
            "Thanks for your email. I’ve reviewed your message and the related account context. "
            "I’ll follow up with the appropriate next step shortly.\n\nBest regards"
        ),
        "provider": "local-fallback",
        "confidence": 0.45,
    }
    client = _get_client()
    if client is None:
        return fallback

    prompt = f"""
Draft a professional reply to the email below using ONLY the supplied ContextIQ evidence.
Do not promise anything that is not supported. Do not invent dates, prices, approvals, or commitments.
The draft will be reviewed by a human before it is saved to Gmail.

EMAIL FROM: {sender}
SUBJECT: {subject}
BODY: {body}

EVIDENCE:
{evidence_text or 'No additional evidence.'}

Return ONLY JSON:
{{"subject":"...","body":"...","confidence":0.0}}
"""
    try:
        response = client.chat.completions.create(
            model=GEMINI_MODEL,
            messages=[
                {"role": "system", "content": "Create cautious evidence-grounded business email drafts. JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        parsed = _extract_json(response.choices[0].message.content if response.choices else "")
        if not parsed:
            return fallback
        confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0.75))))
        return {
            "subject": str(parsed.get("subject") or fallback["subject"]).strip(),
            "body": str(parsed.get("body") or fallback["body"]).strip(),
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "confidence": confidence,
        }
    except Exception:
        return fallback
