# ContextIQ architecture

## Product layers

1. **Identity and integrations** — Google OAuth, Gmail, Calendar, signed ContextIQ session.
2. **Data layer** — SQLite/PostgreSQL-compatible SQLAlchemy models for email, CRM, opportunity, calendar, action, attachment and commitment context.
3. **Deterministic intelligence** — threat checks, priority, process dependency, consequence and approval rules.
4. **Business memory** — local hybrid retrieval using MiniLM semantic embeddings plus TF-IDF lexical relevance.
5. **Generative reasoning** — optional Gemini business insight, Ask ContextIQ answers and reply drafting, all grounded in retrieved evidence.
6. **Guarded actions** — explicit user approval before external side effects; Gmail creates drafts rather than sending mail.
7. **Streamlit experience** — Command Center, Intelligent Inbox, Ask ContextIQ, Action Center and operational views.

## Why hybrid RAG

Semantic embeddings capture meaning even when wording differs. TF-IDF remains useful for exact customer names, identifiers, amounts and unusual terms. ContextIQ combines both signals rather than betting on one retriever.

## Production evolution

The hackathon build intentionally favors a low-cost, inspectable architecture. A production version should add versioned migrations, managed PostgreSQL, a server-side token vault/KMS, asynchronous ingestion jobs, enterprise identity controls, OAuth verification, audit export and persistent vector indexing.
