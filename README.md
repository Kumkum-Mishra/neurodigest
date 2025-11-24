# NeuroDigest

NeuroDigest is a personal content digest and learning-assistant platform that aggregates articles from multiple sources, tracks user engagement (bookmarks and clicks), and provides personalized study recommendations through a Learning Recommendation Module (NDLRM). The app exposes a FastAPI backend and a Streamlit frontend for interactive exploration.

## Key Features
- Aggregate content from multiple sources (HN, Reddit, RSS, Jobs).
- Create weekly digests.
- Track user engagement: bookmarks and article clicks.
- Build a lightweight User Knowledge Profile (UKP) from engagement.
- Generate personalized weekly learning roadmaps for target roles using LLMs.
- Provide practice questions and AI feedback on answers.
- Streamlit-based UI with client-side caching for responsive UX.

## Project Structure
- `mcp_server/` — FastAPI application and routers (auth, user, tutor, preferences).
- `ui/` — Streamlit frontend app and pages (`Dashboard`, `Tutor`).
- `services/` — Business logic: NDLRM, digest generation, embeddings helpers.
- `fetchers/` — Source-specific fetchers for HN, Reddit, RSS, job feeds.
- `storage/` — DB engine and SQLModel models (User, Bookmark, ArticleClick, UserKnowledgeProfile, LearningRoadmap).
- `delivery/` — Email delivery helper for sending digests.
- `scripts/` — Development utilities and tests.

## Quick Start (Development)
These commands assume Windows PowerShell and the project root as the current directory.

1. Create & activate environment

```pwsh
python -m venv venv
& "./venv/Scripts/Activate.ps1"
pip install -r requirements.txt
```

2. Start the FastAPI backend

```pwsh
& "./venv/Scripts/Activate.ps1"
python -m uvicorn mcp_server.main:app --reload
```

3. Start the Streamlit UI (separate terminal)

```pwsh
& "./venv/Scripts/Activate.ps1"
streamlit run ui/app.py
```

Open the Streamlit URL shown in the terminal (typically `http://localhost:8501`).

## Environment Variables
Create a `.env` file at the repo root or set environment variables in your system:
- `DATABASE_URL` — (optional) SQLAlchemy DB URL; default uses SQLite in `storage/db.py`.
- `GROQ_API_KEY` — API key for Groq LLM integration (optional).
- `OLLAMA_URL` — Ollama server URL (optional).
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` — for digest email delivery (optional).

## Database & Schema Notes
- Models use `SQLModel` (SQLAlchemy). The default dev DB is SQLite for quick local usage.
- The project includes a runtime safety check in `services/ndlrm_service.py` that attempts to add the `target_career` column to the `learningroadmap` table if it is missing. This is a stopgap for development environments created before the model change.
- Recommended: adopt a proper migration tool (Alembic) for production and team workflows.

## How Core Flows Work
1. Content fetching: `fetchers/` pull content and can persist items into the storage layer.
2. Digest assembly: `services/digest_service.py` aggregates content into a digest JSON which can be emailed or returned to the UI.
3. Engagement -> Profile: When users bookmark or click articles, these are recorded. `services/ndlrm_service.py` extracts topic keywords and writes a User Knowledge Profile (UKP) used by the NDLRM.
4. Roadmap generation: UI posts `target_career` to `/api/tutor/roadmap`. The backend updates UKP, calls an LLM (Groq or Ollama) to produce structured JSON, and saves a `LearningRoadmap` row.
5. Practice questions and feedback: The UI shows practice questions per roadmap; users can submit answers and the system returns AI feedback via an LLM-backed endpoint.

## Common Commands & Utilities
- Run tests / smoke checks:

```pwsh
& "./venv/Scripts/Activate.ps1"
python scripts/smoke_test.py
```

- Clear all saved roadmaps (development helper): run a small script that deletes `LearningRoadmap` rows. This repository currently contains a helper script used during debugging; use with caution.

## Troubleshooting
- 404s for `/user/bookmarks` — Check for duplicated router prefixes. `mcp_server/main.py` mounts routers with prefixes; ensure individual router files do not re-declare the same prefix.
- Streamlit repeated fetches/timeouts — The UI uses `st.session_state` caching (`cached_get`) to prevent repeated heavy calls across reruns.
- Schema mismatch (`sqlite3.OperationalError: no column named target_career`) — Older DB files may lack the `target_career` column. The code attempts a safe `ALTER TABLE` at runtime in `services/ndlrm_service.py` to add it; however, prefer running migrations or re-creating the DB.

## Development Recommendations
- Add Alembic for migrations and remove runtime ALTERs.
- Introduce background job processing for long LLM calls (e.g., RQ, Celery, or FastAPI BackgroundTasks) and return a job id to the UI for polling.
- Harden LLM outputs by validating JSON via a schema (e.g., `jsonschema`) to avoid UI errors.
- Add unit tests for the NDLRM logic and API endpoints.
