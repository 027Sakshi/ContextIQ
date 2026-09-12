from __future__ import annotations

from typing import Any

from backend.app.services.embedding_service import hybrid_scores


def build_email_text(email: dict) -> str:
    return (
        f"Subject: {email.get('subject', '')}\n"
        f"Sender: {email.get('sender', '')}\n"
        f"Category: {email.get('category', '')}\n"
        f"Body: {email.get('body', '')}"
    )


def retrieve_related_emails(current_email: dict, all_emails: list[dict], top_k: int = 3) -> list[dict]:
    current_id = current_email.get("id")
    candidates = [e for e in all_emails if e.get("id") != current_id]
    if not candidates:
        return []

    scores, model_name = hybrid_scores(
        build_email_text(current_email),
        [build_email_text(item) for item in candidates],
    )
    ranked = sorted(range(len(candidates)), key=lambda i: float(scores[i]), reverse=True)
    results = []
    for index in ranked:
        score = float(scores[index])
        if score <= 0:
            continue
        item = dict(candidates[index])
        item["similarity_score"] = round(score, 4)
        item["retrieval_model"] = model_name
        results.append(item)
        if len(results) >= top_k:
            break
    return results


def build_rag_context(current_email: dict, related_emails: list[dict]) -> str:
    if not related_emails:
        return "No sufficiently similar historical emails were found."
    sections = []
    for index, email in enumerate(related_emails, start=1):
        sections.append(
            "\n".join([
                f"Historical Email {index}",
                f"Subject: {email.get('subject', 'No subject')}",
                f"Sender: {email.get('sender', 'Unknown sender')}",
                f"Category: {email.get('category', 'Unknown')}",
                f"Hybrid similarity: {email.get('similarity_score', 0)}",
                f"Body: {str(email.get('body', ''))[:2000]}",
            ])
        )
    return "\n\n".join(sections)


def run_rag(current_email: dict, all_emails: list[dict], top_k: int = 3) -> dict[str, Any]:
    related = retrieve_related_emails(current_email, all_emails, top_k)
    return {
        "query_email_id": current_email.get("id"),
        "retrieved_count": len(related),
        "related_emails": related,
        "context": build_rag_context(current_email, related),
        "retrieval_model": related[0].get("retrieval_model") if related else "none",
    }
