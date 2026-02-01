# NeuroDigest — Project Report

Author: [Your Name]
Date: Nov 2025
Version: 1.0

---

## Table of Contents

1. Purpose of the Study
2. Background of the Study
3. Literature Survey
4. Introduction
5. Project Analysis
6. Tools and Technologies Used
7. Modules of the Proposed System
8. Methodology
9. Flowchart Overview
10. Conclusion
11. References

Appendices
- A: Database schema summary
- B: API endpoints
- C: Sample JSON payloads

---

## 1. Purpose of the Study

The purpose of this study is to design, develop, and evaluate NeuroDigest — a full-stack personalized content digest and learning-assistant platform. The system collects content from multiple public sources (e.g., Hacker News, Reddit, RSS feeds), tracks user engagement (bookmarks and clicks), synthesizes a compact User Knowledge Profile (UKP), and leverages language models to generate structured weekly learning roadmaps and practice questions tailored to a user's chosen role.

Primary objectives:
- Aggregate and normalize content from heterogeneous sources.
- Capture meaningful engagement signals to infer user interests.
- Generate structured, role-specific learning roadmaps using LLMs.
- Provide practice questions and AI feedback to support learning.
- Ensure a responsive user experience via caching and robust routing.

Intended outcomes:
- A working prototype that demonstrates end-to-end personalization.
- Documentation and architecture to support future extension (migrations, background job orchestration, production deployment).

(Insert an architecture diagram here)

Placeholder: **[INSERT ARCHITECTURE DIAGRAM: `images/architecture_overview.png`]**

---

## 2. Background of the Study

Online content consumption is vast and fragmented. Users often struggle to find a coherent learning path from disparate articles. Traditional recommendation systems focus on relevance and ranking, but do not necessarily transform passively consumed content into a structured learning path. Recent advances in large language models (LLMs) enable the transformation of content + user signals into actionable study plans.

Key motivations:
- Bridge the gap between content discovery and structured learning.
- Use engagement signals (bookmarks, clicks) as a lightweight indicator of interest and topic competency.
- Apply LLMs to produce structured outputs (JSON roadmaps) that can be persisted and presented in a UI.

Relevance:
- Helpful for lifelong learners who browse news and resources but need curated practice plans.
- Useful in interview preparation contexts where practice questions and project ideas accelerate skill building.

---

## 3. Literature Survey

This section reviews related work across three domains: content recommendation, learning path generation, and LLM-based structured generation.

3.1 Content recommendation and engagement modeling
- Collaborative filtering and content-based recommenders.
- Hybrid models that blend behavioral signals (clicks, bookmarks) with content features (keywords, embeddings).
- Papers: Sarwar et al. (2001) on item-based collaborative filtering; Lops et al. (2011) on content-based recommendation.

3.2 Learning path generation
- Adaptive learning systems that generate curricula based on student models.
- Knowledge tracing (e.g., Bayesian Knowledge Tracing, Deep Knowledge Tracing) that estimates proficiency over time.
- Works: Piech et al. (2015) on knowledge tracing; recent adaptive tutoring systems.

3.3 LLM structured output
- Prompting LLMs to return strict JSON and verifying outputs with schemas.
- Robust parsing strategies and fallback mechanisms.
- Papers/notes: OpenAI best practices for structured outputs; research on prompt engineering for constrained formats.

3.4 Summary of gaps addressed
- Integration of lightweight engagement signals (bookmarks) into an on-demand roadmap generator.
- Pragmatic handling of schema drift for rapid dev (runtime PRAGMA + ALTER fallback).
- Streamlit UI patterns for caching to reduce repeated fetches.

(Include a short bibliography block here)

Placeholder: **[INSERT LITERATURE FIGURE: `images/literature_timeline.png`]**

---

## 4. Introduction

NeuroDigest is a prototype designed to show how everyday content consumption can be transformed into actionable learning guidance. It demonstrates the feasibility of producing structured weekly roadmaps and practice questions with minimal user input, leveraging engagement as a signal and LLMs as the generative engine.

Scope:
- Single-user-focused features (login or demo user), digest viewing, bookmarks, knowledge profile, roadmap generation, and AI feedback.
- Development environment targets local deployment (FastAPI + Streamlit + SQLite) with optional LLM integrations (Groq, Ollama).

Limitations:
- No heavy production-grade migration pipeline (Alembic recommended).
- LLM outputs require validation; production must include JSON schema validation.

---

## 5. Project Analysis

This section breaks down requirements, user stories, and non-functional constraints.

5.1 Functional Requirements
- FR1: Fetch content from external sources (HN, Reddit, RSS, jobs) via fetcher modules.
- FR2: Persist content and user interactions in a relational database.
- FR3: Allow users to bookmark articles and record clicks.
- FR4: Compute a user knowledge profile (topic scores) based on engagement.
- FR5: Generate a learning roadmap for a target career/role using LLMs.
- FR6: Persist multiple role-specific roadmaps and present them stacked in the UI.
- FR7: Provide practice questions and collect feedback from users.

5.2 Non-functional Requirements
- NFR1: Reasonable latency for interactive flows (UI caching and TTLs used).
- NFR2: Resilience to unexpected LLM outputs (fallback heuristics and parsing logic).
- NFR3: Graceful handling of schema drift in development (runtime check and ALTER fallback).
- NFR4: Clear UX to avoid repeated fetches on Streamlit reruns.

5.3 User Stories
- As a user, I want to bookmark interesting articles so I can revisit them later.
- As a learner, I want an actionable weekly plan tailored to a role I specify.
- As a user, I want practice questions and AI feedback to improve my answers.

5.4 Risk Analysis
- LLM costs and latency: mitigate with caching, fallbacks, and optional local models (Ollama).
- Data drift and schema mismatch: addressed with runtime checks in dev, but migrate to Alembic for production.

(Insert a table mapping requirements to code modules)

Placeholder: **[INSERT REQUIREMENTS MAPPING TABLE IMAGE: `images/requirements_map.png`]**

---

## 6. Tools and Technologies Used

This section explains each tool and where it is used in the project.

- Python 3.x — Implementation language across backend and UI.
- FastAPI — API server; hosts all REST endpoints in `mcp_server/`.
  - Why: Fast, type-friendly, and simple to extend with modular routers.
- Uvicorn — ASGI server to run FastAPI.
- Streamlit — Frontend UI (`ui/`); chosen for fast interactive prototyping.
- SQLModel / SQLAlchemy — ORM layer used in `storage/models.py`.
- SQLite — Default local DB for development (configurable via environment variable).
- requests — HTTP client for external fetchers and LLM API calls.
- dotenv — Environment variable management.
- Groq / Ollama — Optional LLM backends used by `services/ndlrm_service.py` and `generate_tutor_response()`.
- jsonschema (recommended) — for validating LLM outputs (not mandatory in prototype but suggested).

Where to look:
- Backend core: `mcp_server/main.py`, `mcp_server/tutor/routes_tutor.py`, `services/ndlrm_service.py`.
- UI core: `ui/pages/Tutor.py` and `ui/pages/Dashboard.py`.
- DB models: `storage/models.py` and `storage/db.py`.

---

## 7. Modules of Proposed System

7.1 Fetchers
- Files: `fetchers/hn_fetch.py`, `fetchers/reddit_fetch.py`, `fetchers/rss.py`, `fetchers/jobs_fetch.py`.
- Responsibility: Periodically pull content from public sources and publish into the storage layer.
- Notes: Each fetcher normalizes content into a shared article model.

7.2 Storage
- Files: `storage/models.py`, `storage/db.py`.
- Responsibility: Define SQLModel models and provide DB engine/initialization.
- Key models: `User`, `Bookmark`, `ArticleClick`, `UserKnowledgeProfile`, `LearningRoadmap`.

7.3 Services
- Files: `services/ndlrm_service.py`, `services/digest_service.py`, `services/embeddings.py`.
- Responsibility: Core business logic — UKP computation, LLM calls, roadmap generation, digest assembly.

7.4 API Layer
- Files: `mcp_server/tutor/routes_tutor.py`, `mcp_server/user/routes_user.py`, `mcp_server/main.py`.
- Responsibility: Expose endpoints consumed by Streamlit UI and any third-party clients.

7.5 UI Layer
- Files: `ui/app.py`, `ui/pages/*`.
- Responsibility: Interactive client for users to login, view digest, generate roadmaps, and practice.

7.6 Delivery
- Files: `delivery/emailer.py`.
- Responsibility: Send digests via email; uses SMTP configuration from environment.

(Include a module diagram showing interactions)

Placeholder: **[INSERT MODULE INTERACTION DIAGRAM: `images/module_interaction.png`]**

---

## 8. Methodology

This section documents the step-by-step approach used to develop NeuroDigest.

8.1 Development methodology
- Agile-style iterative development with small, verifiable changes.
- Emphasis on quick prototyping for LLM integration and UX iteration.

8.2 Implementation steps
1. Scaffold application structure: `mcp_server`, `ui`, `services`, `storage`, `fetchers`.
2. Build data model using `SQLModel` and create `storage/db.py` engine.
3. Implement fetchers to collect articles from sources and normalize payloads.
4. Implement the digest assembly service to aggregate items and produce a JSON digest.
5. Create the Streamlit UI skeleton for login, dashboard, and tutor pages.
6. Implement the NDLRM service with topic extraction and UKP computation.
7. Integrate LLMs for roadmap generation with robust parsing logic and fallbacks.
8. Add client-side caching in the UI to avoid repeated fetches.
9. Handle schema drift (runtime PRAGMA + ALTER fallback) to allow older DBs to accept new columns in dev.
10. Clean up and test end-to-end flows; add remediation (clear roadmaps) tools for development.

8.3 Data processing & UKP computation
- Collect bookmarks and clicks from database.
- Extract keywords using a lightweight keyword list and document text (title, summary).
- Aggregate counts and normalize to [0,1] to generate topic scores.
- Persist UKP as JSON in `UserKnowledgeProfile.topic_scores`.

8.4 LLM prompting strategy
- Use a deterministic prompt that requests strict JSON with keys: `week_plan`, `skills_to_learn`, `practice_questions`, `recommended_projects`.
- Post-process model output: remove code-fence wrappers, locate first JSON object, attempt `json.loads`.
- Fallback: If parsing fails, return a small handcrafted roadmap as fallback.

(Insert sample prompt and expected JSON here)

Placeholder: **[INSERT PROMPT EXAMPLE IMAGE/FIGURE: `images/prompt_example.png`]**

---

## 9. Flowchart Overview

This section contains recommended flowcharts and sequence diagrams. Include the following visuals in the indicated places in the final document:

9.1 Overall system flow (high level)
- Start: Fetchers pull content -> Storage -> Digest service assembles digest -> UI displays digest -> User bookmarks/clicks -> UKP updated -> User requests roadmap -> NDLRM calls LLM -> Roadmap persisted -> UI displays roadmap and practice questions.

Placeholder: **[INSERT FLOWCHART IMAGE: `images/flow_overview.png`]**

9.2 Roadmap generation sequence
- Diagram: UI POST `/api/tutor/roadmap` -> `generate_learning_roadmap()` -> UKP update -> LLM call -> parse -> persist roadmap -> return response.

Placeholder: **[INSERT SEQUENCE DIAGRAM: `images/sequence_roadmap.png`]**

9.3 Data model overview (ER diagram)
- Diagram showing `User`, `Bookmark`, `ArticleClick`, `UserKnowledgeProfile`, `LearningRoadmap` and relationships.

Placeholder: **[INSERT ER DIAGRAM: `images/er_model.png`]**

---

## 10. Conclusion

NeuroDigest demonstrates how content consumption can be transformed into structured, actionable learning guidance with modest engineering effort. The prototype integrates content fetchers, engagement tracking, UKP computation, and LLM-driven roadmap generation into a single cohesive prototype. Key achievements:
- End-to-end demonstration of bookmark-driven profile and LLM roadmap generation.
- UX improvements to make the Streamlit UI stable and less noisy (client caching, safe rerun).
- Practical engineering solutions for dev-time schema drift and robust LLM parsing.

Future work:
- Add production-grade migrations (Alembic) and background job handling.
- Add JSON schema validation for LLM outputs and better error reporting.
- Expand UKP computation (embeddings, clustering, interest modeling) and measure learning outcomes.

---

## 11. References

- Sarwar, B., Karypis, G., Konstan, J., & Riedl, J. (2001). Item-based collaborative filtering recommendation algorithms. WWW.
- Piech, C., Bassen, J., Huang, J., et al. (2015). Deep knowledge tracing. NIPS.
- OpenAI. Best practices for prompt design and structured outputs (documentation).
- Other articles, libraries, and docs used during development (include full citations or links here).

---

## Appendices

### Appendix A — Database schema summary
- `User(id, email, hashed_password, ...)`
- `Bookmark(id, user_id, title, url, added_at)`
- `ArticleClick(id, user_id, article_url, article_title, clicked_at)`
- `UserKnowledgeProfile(id, user_id, topic_scores, target_career, last_updated)`
- `LearningRoadmap(id, user_id, week_start, roadmap_data, target_career, generated_at)`

### Appendix B — API endpoints (summary)
- `POST /api/tutor/roadmap` — generate a roadmap (json: {target_career})
- `GET /api/tutor/roadmap` — list saved roadmaps for the current user
- `GET /api/tutor/knowledge-profile` — fetch or compute UKP
- `POST /api/tutor/ask` — ask the tutor / request feedback
- `GET /user/bookmarks` — list bookmarks
- `POST /user/bookmarks` — save a bookmark

### Appendix C — Sample JSON payloads
- Roadmap example:
```json
{
  "week_plan": [
    {"topic": "Neural Networks", "resources": ["Intro tutorial", "Video lecture"]}
  ],
  "skills_to_learn": ["Backpropagation", "Activation functions"],
  "practice_questions": ["Explain backpropagation"],
  "recommended_projects": ["Implement a small MLP"]
}
```

---

## Where to insert images and workflows

Throughout the file I marked the following placeholders. Add images to the `images/` directory and name them accordingly:

- `images/architecture_overview.png` — overall system diagram
- `images/literature_timeline.png` — literature survey timeline
- `images/requirements_map.png` — requirements to modules mapping
- `images/module_interaction.png` — module interaction diagram
- `images/prompt_example.png` — example LLM prompt & expected output
- `images/flow_overview.png` — high-level flowchart
- `images/sequence_roadmap.png` — roadmap sequence diagram
- `images/er_model.png` — ER diagram of DB models

Notes on images:
- Use PNG or SVG for diagrams.
- Keep resolution readable for printed pages (300 DPI recommended if exporting to PDF).
- For flowcharts, consider drawing with draw.io or diagrams.net and exporting PNG.

---

## How this maps to a 25–30 page report

- Each major section above (Purpose, Background, Literature, Introduction, Project Analysis, Tools, Modules, Methodology, Flowcharts, Conclusion, References) can be expanded with screenshots, diagrams, code snippets, and tables.
- Recommended page breakdown (approx):
  - Title, abstract, TOC: 1 page
  - Purpose & background: 2 pages
  - Literature survey: 4–6 pages
  - Introduction & scope: 1 page
  - Project analysis & requirements: 3 pages
  - Tools & technologies: 2 pages
  - Modules & design: 4 pages
  - Methodology & implementation details: 4 pages
  - Flowcharts & diagrams: 3–4 pages
  - Conclusion & future work: 1 page
  - References & appendices: 2–3 pages

This structure yields 25–30 pages when expanded with images and code blocks.

---

If you want, I can now:
- Convert this `REPORT.md` into `REPORT.pdf` using local tools (if you run the command), or
- Break sections into separate MD files and create a small `mkdocs` or static site, or
- Add example screenshots from your UI (I can generate suggested captions and where to place them).

Tell me which you'd like next.