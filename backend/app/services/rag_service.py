from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# ==========================================================
# TEXT BUILDER
# ==========================================================

def build_email_text(email: dict) -> str:
    """
    Convert an email record into searchable text.
    """

    subject = email.get(
        "subject",
        ""
    )

    body = email.get(
        "body",
        ""
    )

    sender = email.get(
        "sender",
        ""
    )

    category = email.get(
        "category",
        ""
    )

    return (
        f"Subject: {subject}\n"
        f"Sender: {sender}\n"
        f"Category: {category}\n"
        f"Body: {body}"
    )


# ==========================================================
# RAG RETRIEVAL
# ==========================================================

def retrieve_related_emails(
    current_email: dict,
    all_emails: list[dict],
    top_k: int = 3
) -> list[dict]:
    """
    Retrieve emails most similar to the current email.

    This is a lightweight local RAG implementation using
    TF-IDF vectors and cosine similarity.

    It does not require an external embedding API.
    """

    if not all_emails:
        return []

    current_id = current_email.get(
        "id"
    )

    documents = []
    candidate_emails = []

    for email in all_emails:

        email_id = email.get(
            "id"
        )

        # Don't retrieve the current email itself.
        if (
            current_id is not None
            and email_id == current_id
        ):
            continue

        text = build_email_text(
            email
        )

        if not text.strip():
            continue

        documents.append(
            text
        )

        candidate_emails.append(
            email
        )

    if not documents:
        return []

    query_text = build_email_text(
        current_email
    )

    try:

        vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=5000
        )

        matrix = vectorizer.fit_transform(
            documents
        )

        query_vector = vectorizer.transform(
            [query_text]
        )

        similarities = cosine_similarity(
            query_vector,
            matrix
        )[0]

    except ValueError:

        return []

    ranked_indices = similarities.argsort()[
        ::-1
    ]

    results = []

    for index in ranked_indices:

        score = float(
            similarities[index]
        )

        if score <= 0:
            continue

        email = dict(
            candidate_emails[index]
        )

        email["similarity_score"] = round(
            score,
            4
        )

        results.append(
            email
        )

        if len(results) >= top_k:
            break

    return results


# ==========================================================
# CONTEXT FORMATTER
# ==========================================================

def build_rag_context(
    current_email: dict,
    related_emails: list[dict]
) -> str:
    """
    Build context that can be sent to an LLM.
    """

    if not related_emails:

        return (
            "No sufficiently similar historical "
            "emails were found."
        )

    sections = []

    for index, email in enumerate(
        related_emails,
        start=1
    ):

        subject = email.get(
            "subject",
            "No subject"
        )

        sender = email.get(
            "sender",
            "Unknown sender"
        )

        category = email.get(
            "category",
            "Unknown"
        )

        body = email.get(
            "body",
            ""
        )

        similarity = email.get(
            "similarity_score",
            0
        )

        sections.append(
            "\n".join(
                [
                    f"Historical Email {index}",
                    f"Subject: {subject}",
                    f"Sender: {sender}",
                    f"Category: {category}",
                    f"Similarity: {similarity}",
                    f"Body: {body[:2000]}",
                ]
            )
        )

    return "\n\n".join(
        sections
    )


# ==========================================================
# COMPLETE RAG RESULT
# ==========================================================

def run_rag(
    current_email: dict,
    all_emails: list[dict],
    top_k: int = 3
) -> dict[str, Any]:
    """
    Run the complete retrieval step.
    """

    related_emails = (
        retrieve_related_emails(
            current_email=current_email,
            all_emails=all_emails,
            top_k=top_k
        )
    )

    context = build_rag_context(
        current_email=current_email,
        related_emails=related_emails
    )

    return {
        "query_email_id": current_email.get(
            "id"
        ),
        "retrieved_count": len(
            related_emails
        ),
        "related_emails": related_emails,
        "context": context,
    }