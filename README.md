## AI/ML Highlights

ContextIQ combines **semantic retrieval, lexical search, contextual data fusion, and grounded LLM reasoning** to build an AI system that can understand business context rather than process each message independently.

### Hybrid RAG Pipeline

The retrieval layer combines two complementary approaches:

- **MiniLM Embeddings** — captures semantic similarity between queries and business content.
- **TF-IDF Retrieval** — preserves exact keywords, names, terms, and lexical relevance.
- **Context Fusion** — connects retrieved information across emails, documents, meetings, contacts, and business records.
- **Evidence Grounding** — passes relevant retrieved context to the reasoning layer before generating a response.

```text
                 User Query
                     │
                     ▼
          ┌─────────────────────┐
          │   Query Processing  │
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   MiniLM Embeddings       TF-IDF Search
   Semantic Retrieval     Lexical Retrieval
          │                     │
          └──────────┬──────────┘
                     ▼
             Hybrid Ranking
                     │
                     ▼
          Contextual Evidence
                     │
                     ▼
          Grounded AI Reasoning
                     │
                     ▼
       Answer / Recommendation
```

---

## Core AI Capabilities

| Capability | Implementation |
|---|---|
| **Semantic Search** | SentenceTransformer MiniLM embeddings for contextual similarity |
| **Hybrid Retrieval** | Dense embeddings combined with TF-IDF lexical retrieval |
| **Retrieval-Augmented Generation** | Relevant business evidence retrieved before LLM reasoning |
| **Context Fusion** | Connects Gmail, Calendar, documents, contacts, and business records |
| **Grounded Q&A** | Generates answers using retrieved evidence instead of isolated prompting |
| **Commitment Detection** | Identifies requests, follow-ups, promises, and actionable communication |
| **Priority Intelligence** | Surfaces important conversations and business consequences |
| **AI Response Generation** | Generates contextual replies using retrieved conversation history |
| **Human-in-the-Loop AI** | Requires approval before consequential external actions |

---

## Context-Aware Intelligence

A major focus of ContextIQ is moving beyond:

```text
Email → Prompt → LLM Response
```

and instead building:

```text
Email
  │
  ├── Previous Conversations
  ├── Calendar Events
  ├── Documents
  ├── Contacts
  ├── Business Context
  └── Commitments
           │
           ▼
      Hybrid Retrieval
           │
           ▼
      Relevant Evidence
           │
           ▼
      AI Reasoning
           │
           ▼
   Decision + Recommended Action
```

This allows the system to answer questions using the **surrounding business context**, not only the currently selected message.

---

## Example Intelligence Flow

Suppose a customer sends an email asking for an update on a proposal.

ContextIQ can:

1. Understand the incoming message and identify its intent.
2. Retrieve previous conversations with the customer.
3. Find related documents, meetings, and business context.
4. Detect previous commitments or unresolved follow-ups.
5. Rank the most relevant evidence using hybrid retrieval.
6. Generate an evidence-grounded recommendation.
7. Prepare a contextual response or suggested action.
8. Require user approval before creating an external action.

This demonstrates the core idea behind ContextIQ:

> **Retrieve first. Reason with context. Act only with approval.**

---

## Human-in-the-Loop AI

ContextIQ separates **AI reasoning** from **action execution**.

```text
AI Recommendation
        │
        ▼
Generated Action
        │
        ▼
Human Review
        │
        ▼
Explicit Approval
        │
        ▼
External Action
```

For example, ContextIQ can generate an email response, but instead of automatically sending it, the system can create a **Gmail draft for user review**.

This keeps AI useful while maintaining user control over consequential actions.

---

## Technology Stack

| Area | Technologies |
|---|---|
| **Language** | Python |
| **AI / ML** | SentenceTransformers, MiniLM, Scikit-learn |
| **Retrieval** | Semantic Embeddings, TF-IDF, Cosine Similarity, Hybrid RAG |
| **Generative AI** | Google Gemini |
| **Backend** | FastAPI |
| **Frontend** | Streamlit |
| **Database** | SQLite, SQLAlchemy |
| **Integrations** | Gmail API, Google Calendar API |
| **Authentication** | Google OAuth 2.0 |
| **Document Processing** | PyPDF, python-docx |
| **Testing** | Pytest |

---

## Project Structure

```text
ContextIQ/
│
├── ai/                     # Retrieval, embeddings and AI reasoning
├── backend/
│   └── app/                # FastAPI APIs and business logic
├── frontend/               # Streamlit interface
├── data/                   # Application data
├── docs/                   # Project documentation
├── scripts/                # Development utilities
├── tests/                  # Automated tests
│
├── .env.example
├── requirements.txt
├── streamlit_app.py
└── README.md
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/027Sakshi/ContextIQ.git
cd ContextIQ
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

**Windows**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Configure the required Google OAuth credentials and optional Gemini API key inside `.env`.

### 5. Start the application

Backend:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
streamlit run frontend/app.py --server.port 8501
```

Open:

```text
http://localhost:8501
```

---

## Key Engineering Principles

- **Retrieval before generation** to reduce unsupported LLM responses.
- **Hybrid search** instead of relying only on vector similarity.
- **Context fusion** across multiple business information sources.
- **Evidence-backed reasoning** for explainable AI outputs.
- **Human approval gates** before external actions.
- **User-scoped data and authentication** for safer multi-user workflows.
- **Modular AI and backend architecture** for future model and retrieval upgrades.

---

## Future Scope

- Vector database support for larger knowledge bases.
- Learned reranking for improved retrieval quality.
- Long-term organizational memory and temporal reasoning.
- Additional enterprise connectors and business data sources.
- Retrieval and generation evaluation pipelines.
- Production observability and scalable deployment.

---

## Author

**Sakshi Giglani**

[GitHub](https://github.com/027Sakshi) •
[LinkedIn](https://www.linkedin.com/in/sakshi-giglani/)

---

<p align="center">
  <strong>ContextIQ</strong><br>
  Turning fragmented business context into evidence-grounded intelligence.
</p>
