# NeuroDigest — Project Summary

## Title
NeuroDigest — Personalized Content Digest & Learning Assistant

## Short Summary
NeuroDigest builds personalized digests from multiple sources (HN, Reddit, RSS, job feeds), tracks user engagement (bookmarks, clicks), and uses a learning recommendation module (NDLRM) to generate weekly learning roadmaps and practice questions. It provides a Streamlit UI for users to view digests, bookmarks, knowledge profiles, and tutor features, and a FastAPI backend for APIs, auth, and services.

## Core Components
- `mcp_server/` (FastAPI)
  - `main.py`: app factory and router includes.
  - `auth/`: authentication-related utilities and routes (`auth_utils.py`, `routes_auth.py`).
  - `user/`: user endpoints (preferences, bookmarks) in `routes_user.py`.
  - `tutor/`: tutor endpoints for roadmap generation and knowledge profile in `routes_tutor.py`.
  - `preferences/`, `tutor/`, `user/`: modular FastAPI routers.

- `ui/` (Streamlit)
  - `app.py`: entrypoint and landing/dashboard navigation.
  - `pages/Dashboard.py`: digest viewing, bookmark actions, cached fetches.
  - `pages/Tutor.py`: NDLRM UI — generate roadmaps, knowledge profile, practice questions (client-side caching, safe rerun, normalized roadmap handling).
  - Pages are reactive Streamlit components; `session_state` is used for caching and UI state.

- `services/`
  - `ndlrm_service.py`: main learning roadmap generation logic, topic extraction from engagement, UKP calculation, LLM calls, and persistence.
  - `digest_service.py`: digest construction and summarization (fetch + assemble content). 
  - `embeddings.py`, `ndlrm_service.py` (other helpers) used for advanced processing.

- `fetchers/`
  - Source-specific fetchers: `hn_fetch.py`, `reddit_fetch.py`, `rss.py`, `jobs_fetch.py`.
  - These pull content and feed into storage or digest pipelines.

- `storage/`
  - `db.py`: SQLModel / SQLAlchemy engine and DB initialization.
  - `models.py`: SQLModel tables (`User`, `Bookmark`, `ArticleClick`, `UserKnowledgeProfile`, `LearningRoadmap`, etc.).
  - `archive/`: stored past digests.

- `delivery/`
  - `emailer.py`: utilities for sending digests via email.

- `scripts/`
  - `smoke_test.py`, `test_roadmap_local.py`: local checks and development utilities.

## Data Flow / Workflow (high-level)
1. Fetch content: `fetchers/` pull data from sources and write into `storage`.
2. Digest generation: `services/digest_service.py` aggregates and formats digest JSON.
3. User interaction: Streamlit UI (`ui/`) calls FastAPI endpoints to read digests, save bookmarks, and request tutor operations.
4. Engagement -> Profile: Bookmarks and clicks are stored (`Bookmark`, `ArticleClick`); `services/ndlrm_service.py` extracts topic keywords and builds the User Knowledge Profile (UKP).
5. Roadmap generation: UI posts to `/api/tutor/roadmap` which calls `generate_learning_roadmap()`; this calls an LLM (Groq or Ollama) and persists a `LearningRoadmap` row.
6. Practice & Feedback: Practice questions are shown in UI; user answers can be sent to `/api/tutor/ask` which calls `generate_tutor_response()` to get feedback from an LLM.

## Tools, Libraries & Where They Are Used
- Python 3.x — main language for backend and UI.
- FastAPI — backend API server (`mcp_server/`).
- Uvicorn — ASGI server used to run FastAPI.
- Streamlit — frontend UI (`ui/`).
- SQLModel (built on SQLAlchemy) — models & DB ORM (`storage/models.py`).
- SQLite (default) — local DB for dev (configurable via `storage/db.py`).
- requests — HTTP calls to external APIs and LLM endpoints.
- dotenv (`python-dotenv`) — load environment variables (API keys, endpoints).
- Groq / Ollama — optional LLM backends used by `services/ndlrm_service.py` and `generate_tutor_response()`.
- json, time, datetime — standard libs for serialization and timestamps.

## Skills You Will Learn Working Through This Project
- Building a FastAPI backend and modular routers.
- Designing SQLModel/SQLAlchemy models & simple migrations.
- Integrating Streamlit for rapid UI prototyping and caching UX with `session_state`.
- Working with LLMs (Groq/Ollama) for structured JSON outputs and fallback parsing.
- Handling schema drift and safe migrations (PRAGMA checks, ALTER TABLE in dev).
- Client-side caching strategies to prevent repeated API calls in reactive UIs.
- Debugging and deploying local dev servers (uvicorn, Streamlit) on Windows.

## How to Run Locally (dev quick start)
1. Create and activate the venv (Windows PowerShell):

```pwsh
python -m venv venv
& "./venv/Scripts/Activate.ps1"
pip install -r requirements.txt
```

2. Start the backend (FastAPI):

```pwsh
& "./venv/Scripts/Activate.ps1"
python -m uvicorn mcp_server.main:app --reload
```

3. Start the Streamlit UI in a separate terminal:

```pwsh
& "./venv/Scripts/Activate.ps1"
streamlit run ui/app.py
```

4. Open the Streamlit URL shown in the terminal (usually `http://localhost:8501`).

Notes:
- Ensure any required environment variables are set in `.env` (`GROQ_API_KEY`, `OLLAMA_URL`, etc.).
- If adding new models or fields, run `init_db()` (or allow the small runtime ALTERs used for `target_career`) in `services/ndlrm_service.py`.

## Development Notes & Known Gotchas
- Router prefixes: `mcp_server/main.py` includes routers with prefixes; ensure router-level prefixes are not duplicated to avoid 404s.
- Streamlit reruns: Streamlit's reactive model triggers re-runs; UI uses `st.session_state` caching and a `_safe_rerun()` helper to handle different Streamlit versions.
- Roadmap `target_career` column: older DBs may not have this column — the code now includes a safe PRAGMA + `ALTER TABLE` attempt before inserts. For production you should apply a migration instead.
- API response shapes: endpoints may return slightly different shapes; the UI normalizes roadmap payloads (see `ui/pages/Tutor.py`) to handle `dict`, `list`, or JSON-string shapes.

## Files of Interest (quick map)
- `mcp_server/main.py` — app startup & router includes
- `mcp_server/user/routes_user.py` — user bookmarks and preferences endpoints
- `mcp_server/tutor/routes_tutor.py` — tutor endpoints (roadmap, knowledge-profile, ask)
- `services/ndlrm_service.py` — roadmap generation and UKP logic
- `ui/app.py` — Streamlit entry
- `ui/pages/Tutor.py` — Tutor UI (generate roadmap, show practice Qs)
- `storage/models.py` & `storage/db.py` — DB models and engine

## Suggested Next Improvements
- Add a proper Alembic migration workflow rather than runtime ALTERs for schema changes.
- Add async background tasks or job queue (RQ/Celery/Redis) for long-running LLM roadmap generation; return a job id and poll for completion.
- Add unit/integration tests for `services/ndlrm_service.py` and API endpoints.
- Improve LLM output validation and use JSON schema validation for roadmap shapes.
- Add an export/backup endpoint for roadmaps before destructive operations.

---

If you want, I can also:
- Add this as `README.md` (instead of `summary.md`) and update `pyproject`/`package` metadata.
- Create a short printable README (`README.md`) and a longer `DEVELOPER.md` containing setup + migration steps.
- Generate a one-click Streamlit button in `ui/pages/Tutor.py` to clear (or export+clear) saved roadmaps.

Tell me which of those you'd like next and I'll add it.