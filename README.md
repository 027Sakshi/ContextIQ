# ContextIQ

**AI business decision intelligence for Gmail.**

ContextIQ turns inbox activity into an evidence-backed operating layer for work: it connects Gmail, Calendar, CRM-style account context, attachments, commitments, business risk, and human-approved actions in one Streamlit product.

## Why ContextIQ

Email tools usually stop at summarization. ContextIQ is designed around a full decision loop:

**Understand → Retrieve → Connect → Reason → Explain → Approve → Act → Track**

A high-value customer email can be connected to related messages, account/deal context, documents, meetings and commitments. ContextIQ then surfaces what matters, explains why, answers business questions using retrieved evidence, and can create a Gmail draft or Calendar event only after human approval.

## Hackathon highlights

- **Google account sign-in** with one identity for ContextIQ, Gmail and Calendar.
- **Per-user encrypted OAuth token storage**; tokens and client credentials are ignored by Git.
- **Semantic business memory** using local SentenceTransformers (`all-MiniLM-L6-v2`) plus TF-IDF hybrid retrieval.
- **Unified RAG** across emails, attachments, CRM records, opportunities, contacts, companies, calendar events and detected commitments.
- **Ask ContextIQ** business copilot with evidence references instead of unsupported answers.
- **Gmail thread memory** through stored Gmail thread IDs.
- **Commitment intelligence** for requests/promises and due-date signals.
- **Human-approved AI actions**: create Gmail drafts and Google Calendar events; never auto-send email.
- **Explainable consequence/decision engine** with risk, priority and business context.
- **Streamlit-only product UI** with a Command Center, Inbox, Action Center, accounts/context views and evidence panels.
- **Free-first stack**: Python, Streamlit, FastAPI, SQLite, SQLAlchemy, scikit-learn, SentenceTransformers and Google APIs; Gemini is optional and has a local fallback path.

## Architecture

```text
Google Account
   │
   ├── Gmail ────────────────┐
   └── Calendar ─────────────┤
                             ▼
                     Ingestion / parsing
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
       Emails            Attachments        Business data
          │                  │            CRM / deals / people
          └──────────────────┼──────────────────┘
                             ▼
                     Business knowledge
                             │
                  MiniLM + TF-IDF hybrid RAG
                             │
                             ▼
                  Evidence-grounded reasoning
                             │
               ┌─────────────┼─────────────┐
               ▼             ▼             ▼
          Ask ContextIQ   Decisions    Reply / Calendar
                                           │
                                    Human approval gate
                                           │
                                           ▼
                                      Google action
```

## Quick start

Requirements: Python 3.12+, a Google Cloud OAuth Web client for Google login/Gmail/Calendar, and optionally a Gemini API key.

```powershell
# from the repository root
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Create a long local session secret in `.env`:

```powershell
$secret = -join ((48..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
(Get-Content .env) -replace 'replace-with-a-long-random-secret', $secret | Set-Content .env
```

Add your Google Web OAuth client JSON at:

```text
credentials/google_oauth_client.json
```

The `credentials/` directory is intentionally ignored by Git.

For Google Cloud setup see [docs/GOOGLE_OAUTH_SETUP.md](docs/GOOGLE_OAUTH_SETUP.md).

Seed a safe local demo workspace if desired:

```powershell
$env:DEMO_USER_EMAIL="your-google-account@gmail.com"
python -m backend.app.scripts.seed_data
python -m backend.app.scripts.seed_calendar
```

Start ContextIQ:

```powershell
.\scripts\run_dev.ps1
```

Then open `http://localhost:8501`.

## Tests

```powershell
python -m compileall -q backend frontend ai tests
python -m pytest -q
```

Or run the full pre-demo gate:

```powershell
.\scripts\check_release.ps1
```

## Security / product boundaries

- Never commit `.env`, Google OAuth client secrets, refresh tokens, local databases or imported attachments.
- ContextIQ signs its API session and scopes business records to the authenticated user.
- Stored Google refresh tokens are encrypted per user on disk.
- Gmail reply automation creates a **draft only**. ContextIQ does not automatically send mail.
- High-impact actions require explicit user approval.
- Gmail access uses a Google restricted scope. Hackathon/demo OAuth can stay in Google Cloud **Testing** with explicit test users. A public production release must complete the applicable Google verification/security requirements.

## Demo

Use [docs/HACKATHON_DEMO.md](docs/HACKATHON_DEMO.md) for the recommended 3–5 minute judge flow.

## Branches

- `main` — stable / final demo releases
- `develop` — active product development
