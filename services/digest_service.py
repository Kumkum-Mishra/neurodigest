# services/digest_service.py
import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import select, Session
from storage.db import engine   # <- use engine directly for manual sessions
from storage.models import UserPreference

# load env
load_dotenv()

# your existing fetchers
from fetchers.hn_fetch import fetch_hn_articles, fetch_hn_jobs
from fetchers.jobs_fetch import fetch_jobs_articles
from fetchers.reddit_fetch import fetch_reddit_articles
from fetchers.rss_fetch import fetch_rss_articles

from extract_content import extract_article_text
from summarizer import summarize_text  # summarizer package

# storage
STORAGE_DIR = Path("storage")
ARCHIVE_DIR = STORAGE_DIR / "archive"
LATEST_FILE = STORAGE_DIR / "latest_digest.json"

os.makedirs(ARCHIVE_DIR, exist_ok=True)

# fallback keywords if user has no preferences (student placement focused)
KEYWORDS = [
    # Interviews & DSA
    "interview", "coding round", "system design", "dsa", "data structures", "algorithms",
    "behavioral", "resume", "placement", "campus hiring", "internship",

    # Core tech & platforms
    "python", "java", "c++", "javascript", "react", "node", "spring", "django",
    "github", "docker", "kubernetes", "cloud", "aws", "azure", "gcp",

    # AI/ML trends
    "ai", "machine learning", "deep learning", "llm", "gen ai", "openai", "anthropic",
    "google", "gemini", "microsoft", "meta", "deepseek", "perplexity",

    # Career & industry
    "hiring", "placement drive", "offer", "intern", "graduate program", "fresher",
    "startup", "launch", "research", "paper", "arxiv", "trends",
]


def is_relevant(title: str, content: str) -> bool:
    """Quick relevance check using fallback global keywords."""
    full = (title + " " + (content or "")).lower()
    return any(k.lower() in full for k in KEYWORDS)


def get_all_articles(limit_per_source=5):
    articles = []
    try:
        articles.extend(fetch_hn_articles(limit=limit_per_source))
    except Exception as e:
        print("hn fetch error:", e)
    try:
        articles.extend(fetch_hn_jobs(limit=limit_per_source))
    except Exception as e:
        print("hn jobs fetch error:", e)
    # Job boards
    try:
        articles.extend(fetch_jobs_articles(limit_per_source))
    except Exception as e:
        print("job boards fetch error:", e)
    try:
        articles.extend(fetch_reddit_articles(limit=limit_per_source))
    except Exception as e:
        print("reddit fetch error:", e)
    try:
        articles.extend(fetch_rss_articles(limit=limit_per_source))
    except Exception as e:
        print("rss fetch error:", e)

    # dedupe by url
    seen = set()
    unique = []
    for a in articles:
        url = a.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(a)
    return unique


def build_digest_items(limit_per_source=8, max_articles=25):
    """Fetch → extract → summarize → return digest items."""
    articles = get_all_articles(limit_per_source=limit_per_source)
    items = []
    # Prefer student/placement relevance early by simple keyword boost
    prioritized = []
    for a in articles:
        title = (a.get("title") or "").lower()
        score = 0
        for k in ["interview", "dsa", "system design", "intern", "placement", "hiring", "ai", "llm", "machine learning", "leetcode", "geeksforgeeks", "techcrunch", "arxiv"]:
            if k in title:
                score += 1
        prioritized.append((score, a))
    prioritized.sort(key=lambda x: x[0], reverse=True)

    for _, a in prioritized[:max_articles]:
        title = a.get("title")
        url = a.get("url")
        print("Fetching:", title)
        text = extract_article_text(url)
        if not text:
            continue
        if not is_relevant(title, text):
            print("Skipping irrelevant:", title)
            continue

        summary_raw = summarize_text(text)

        def _fallback_bullets_from_text(content: str) -> list[str]:
            # naive sentence split fallback
            candidates = [s.strip().rstrip(" .") for s in content.replace("\n", " ").split(". ") if s.strip()]
            return candidates[:4]

        # primary attempt: split lines returned by summarizer
        bullets = [
            line.strip().rstrip(" .")
            for line in (summary_raw or "").replace("\r", "").splitlines()
            if line.strip()
        ]
        if len(bullets) < 2:
            bullets = [s.strip().rstrip(" .") for s in (summary_raw or "").split(". ") if s.strip()]
        if len(bullets) < 2:
            print("Summary too short or failed; falling back to sentence split")
            bullets = _fallback_bullets_from_text(text)
        # LAST RESORT: ensure at least one bullet from title if everything failed
        if not bullets:
            bullets = [title]

        def _categorize(title_val: str, bullet_list: list[str], article_url: str) -> list[str]:
            blob = (title_val or "") + " " + " ".join(bullet_list)
            low = blob.lower()
            tags: list[str] = []
            if any(k in low for k in ["interview", "dsa", "system design", "leetcode", "hackerrank", "geeksforgeeks"]):
                tags.append("interview")
            if any(k in low for k in ["ai", "llm", "machine learning", "deep learning", "arxiv", "research", "chatgpt", "gemini", "openai", "anthropic"]):
                tags.append("ai")
            if any(k in low for k in ["hiring", "internship", "placement", "career", "resume", "offer", "graduate program", "fresher"]):
                tags.append("career")
            if not tags:
                tags.append("general")
            return tags

        # also include a plain summary string for UI fallbacks
        summary_text = ". ".join(bullets[:4])

        # derive company from url domain heuristics
        def _infer_company(url_val: str) -> str | None:
            try:
                host = url_val.split("//", 1)[-1].split("/", 1)[0].lower()
            except Exception:
                host = ""
            host = host.replace("www.", "")
            mapping = {
                "google": "Google",
                "alphabet": "Google",
                "amazon": "Amazon",
                "aws": "Amazon",
                "apple": "Apple",
                "meta": "Meta",
                "facebook": "Meta",
                "netflix": "Netflix",
                "microsoft": "Microsoft",
                "openai": "OpenAI",
                "tesla": "Tesla",
                "uber": "Uber",
                "airbnb": "Airbnb",
                "stripe": "Stripe",
                "databricks": "Databricks",
                "snowflake": "Snowflake",
                "nvidia": "NVIDIA",
            }
            for key, name in mapping.items():
                if key in host:
                    return name
            # fallback: take first label capitalized
            if host:
                return host.split(".", 1)[0].capitalize()
            return None

        def _infer_role(blob_text: str) -> str | None:
            roles = [
                "software engineer", "sde", "sde i", "sde ii", "backend engineer",
                "frontend engineer", "full stack", "machine learning engineer",
                "data scientist", "data engineer", "ml research", "research engineer",
                "intern", "software intern", "ml intern", "data science intern",
                "site reliability", "devops", "cloud engineer",
            ]
            low = blob_text.lower()
            for r in roles:
                if r in low:
                    return r
            return None

        def _extract_salary_hint(blob_text: str) -> str | None:
            import re
            patterns = [
                r"\b\$\s?\d{2,3}(,\d{3})*(\+)?\b",
                r"\b\d+\s?(lpa|lac|lakh)\b",
                r"\b\d{2,3}k\b",
            ]
            for pat in patterns:
                m = re.search(pat, blob_text.lower())
                if m:
                    return m.group(0)
            return None

        text_blob_for_meta = (title or "") + " " + " ".join(bullets)

        item = {
            "title": title,
            "url": url,
            "bullets": bullets[:4],
            "tags": _categorize(title, bullets, url or ""),
            "summary": summary_text,
            "company": _infer_company(url or "") if url else None,
            "role": _infer_role(text_blob_for_meta),
            "salary_hint": _extract_salary_hint(text_blob_for_meta),
        }
        items.append(item)
    return items


def save_digest(items):
    """Save latest digest + archive snapshot."""
    payload = {"generated_at": int(time.time()), "items": items}
    with open(LATEST_FILE, "w", encoding="utf8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    fname = ARCHIVE_DIR / f"digest_{int(time.time())}.json"
    with open(fname, "w", encoding="utf8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def run_full_pipeline():
    """Fetch -> summarize -> save -> return payload"""
    items = build_digest_items()
    payload = save_digest(items)
    print("✅ Digest built with", len(items), "articles")
    return payload

def load_latest_digest():
    if LATEST_FILE.exists():
        with open(LATEST_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    return {"generated_at": None, "items": []}


# ----------------------------
# Preferences integration (uses direct Session(engine))
# ----------------------------
def get_user_preferences(user_id: int):
    """
    Open a manual session for service-layer DB access.
    """
    with Session(engine) as session:
        prefs = (
            session.exec(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            .first()
        )
        if prefs:
            keywords = [
                kw.strip().lower() for kw in (prefs.keywords or "").split(",") if kw.strip()
            ]
            sources = [
                src.strip().lower() for src in (prefs.sources or "").split(",") if src.strip()
            ]
            return {
                "keywords": keywords,
                "sources": sources,
                "match_mode": getattr(prefs, "match_mode", "or"),
            }
        return {"keywords": [], "sources": [], "match_mode": "or"}


def load_personalized_digest(user_id: int):
    """Filter latest digest according to user preferences."""
    digest = load_latest_digest()
    prefs = get_user_preferences(user_id)

    keywords = prefs.get("keywords", [])
    sources = prefs.get("sources", [])
    match_mode = prefs.get("match_mode", "or")

    if not keywords and not sources:
        return digest

    filtered = []
    for article in digest.get("items", []):
        text_blob = " ".join([
            article.get("title", ""),
            " ".join(article.get("bullets", []))
        ]).lower()
        url = article.get("url", "").lower()

        # ✅ improved matching
        kw_match = any(kw.lower() in text_blob for kw in keywords) if keywords else False
        src_match = any(src.lower() in url for src in sources) if sources else False

        if match_mode == "or":
            if kw_match or src_match:
                filtered.append(article)
        else:  # AND logic
            if (not keywords or kw_match) and (not sources or src_match):
                filtered.append(article)

    print(f"🔎 Personalized digest for user {user_id}: {len(filtered)} / {len(digest.get('items', []))} items matched")

    return {"generated_at": digest.get("generated_at"), "items": filtered}
