# services/digest_service.py
import os
import time
import json
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from sqlmodel import select, Session
from storage.db import engine   # <- use engine directly for manual sessions
from storage.models import UserPreference, ArticleClick, EngagementHistory, UserKnowledgeProfile

# load env
load_dotenv()

# your existing fetchers
from fetchers.hn_fetch import fetch_hn_articles, fetch_hn_jobs
from fetchers.jobs_fetch import fetch_jobs_articles
from fetchers.reddit_fetch import fetch_reddit_articles
from fetchers.rss_fetch import fetch_rss_articles

from extract_content import extract_article_text
from summarizer import summarize_text  # summarizer package

# Optional embeddings (may not be available on Vercel)
try:
    from services.embeddings import keyword_match_score, user_preference_match_score
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    # Fallback functions if embeddings not available
    def keyword_match_score(article_text: str, user_keywords: List[str]) -> float:
        """Fallback: simple keyword matching without embeddings."""
        if not user_keywords:
            return 0.5
        article_lower = article_text.lower()
        matches = sum(1 for kw in user_keywords if kw.lower() in article_lower)
        return min(1.0, matches / len(user_keywords)) if user_keywords else 0.5
    
    def user_preference_match_score(article_text: str, article_url: str, 
                                    user_keywords: List[str], user_sources: List[str]) -> float:
        """Fallback: simple matching without embeddings."""
        scores = []
        if user_keywords:
            scores.append(keyword_match_score(article_text, user_keywords))
        if user_sources:
            url_lower = article_url.lower()
            source_match = any(src.lower() in url_lower for src in user_sources)
            scores.append(1.0 if source_match else 0.0)
        return float(sum(scores) / len(scores)) if scores else 0.5

from urllib.parse import urlparse
import math
import re

# storage
STORAGE_DIR = Path("storage")
ARCHIVE_DIR = STORAGE_DIR / "archive"
LATEST_FILE = STORAGE_DIR / "latest_digest.json"

# Try to create archive directory, but don't fail if file system is read-only (serverless)
# Vercel serverless functions have read-only file system
FILE_STORAGE_AVAILABLE = False
try:
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    # Test write access
    test_file = ARCHIVE_DIR / ".test_write"
    try:
        test_file.write_text("test")
        test_file.unlink()
        FILE_STORAGE_AVAILABLE = True
    except Exception:
        FILE_STORAGE_AVAILABLE = False
except Exception as e:
    print(f"File storage not available (read-only filesystem): {e}")
    FILE_STORAGE_AVAILABLE = False

# ============================================================
# MSNRR: Multi-Signal News Ranking & Relevance Algorithm
# ============================================================

# Domain Authority Scores (DAS)
DOMAIN_AUTHORITY_SCORES = {
    "arxiv.org": 1.0,
    "ai.google": 0.95,
    "google.com": 0.95,
    "nvidia.com": 0.92,
    "kaggle.com": 0.85,
    "github.com": 0.80,
    "openai.com": 0.90,
    "anthropic.com": 0.88,
    "deepmind.com": 0.92,
    "huggingface.co": 0.85,
    "medium.com": 0.5,
    "reddit.com": 0.4,
    "news.ycombinator.com": 0.7,
    "techcrunch.com": 0.75,
    "wired.com": 0.70,
    "theverge.com": 0.65,
}


def get_domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    try:
        domain = urlparse(url).netloc.replace("www.", "").lower()
        return domain
    except Exception:
        return ""


def compute_domain_authority_score(article_url: str) -> float:
    """
    2️⃣ Domain Authority Score (DAS)
    Returns value in [0, 1].
    """
    domain = get_domain_from_url(article_url)
    if not domain:
        return 0.2  # Unknown domain
    
    # Check exact match first
    if domain in DOMAIN_AUTHORITY_SCORES:
        return DOMAIN_AUTHORITY_SCORES[domain]
    
    # Check partial matches (e.g., "blog.google.com" -> matches "google.com")
    for known_domain, score in DOMAIN_AUTHORITY_SCORES.items():
        if known_domain in domain or domain in known_domain:
            return score
    
    return 0.2  # Default for unknown domains


def compute_popularity_score(article: dict) -> float:
    """
    3️⃣ Popularity Score (PS)
    For Reddit/HN: use upvotes, comments.
    Returns value in [0, 1].
    """
    # Check if article has popularity metrics
    upvotes = article.get("score", 0) or article.get("upvotes", 0) or 0
    comments = article.get("num_comments", 0) or article.get("comments", 0) or 0
    
    # Normalize: assume max upvotes = 1000, max comments = 100
    normalized_upvotes = min(1.0, upvotes / 1000.0)
    normalized_comments = min(1.0, comments / 100.0)
    
    # Weighted average
    ps = 0.7 * normalized_upvotes + 0.3 * normalized_comments
    return min(1.0, max(0.0, ps))


def compute_recency_score(article: dict) -> float:
    """
    4️⃣ Recency Score (RS)
    RS = e^(-age_in_hours / 24)
    Returns value in [0, 1].
    """
    published = article.get("published") or article.get("published_at") or article.get("time")
    if not published:
        return 0.5  # Neutral if no timestamp
    
    try:
        if isinstance(published, str):
            # Try parsing ISO format or other formats
            from datetime import datetime
            published_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            published_ts = published_dt.timestamp()
        else:
            published_ts = float(published)
        
        current_ts = time.time()
        age_hours = (current_ts - published_ts) / 3600.0
        
        # RS = e^(-age_in_hours / 24)
        rs = math.exp(-age_hours / 24.0)
        return min(1.0, max(0.0, rs))
    except Exception:
        return 0.5  # Neutral on error


def compute_summarization_quality_score(summary: str) -> float:
    """
    5️⃣ Summarization Quality Score (SQS)
    Based on length + coherence (sentence similarity).
    Returns value in [0, 1].
    """
    if not summary or not summary.strip():
        return 0.0
    
    # Length score (optimal: 100-500 chars)
    length = len(summary)
    if length < 50:
        length_score = length / 50.0
    elif 50 <= length <= 500:
        length_score = 1.0
    else:
        length_score = max(0.5, 1.0 - (length - 500) / 1000.0)
    
    # Coherence: check for sentence structure (periods, capitalization)
    sentences = [s.strip() for s in summary.split(". ") if s.strip()]
    if len(sentences) < 2:
        coherence_score = 0.5
    else:
        # Check if sentences start with capital letters
        proper_sentences = sum(1 for s in sentences if s and s[0].isupper())
        coherence_score = proper_sentences / len(sentences) if sentences else 0.5
    
    # Weighted average
    sqs = 0.6 * length_score + 0.4 * coherence_score
    return min(1.0, max(0.0, sqs))


def compute_user_preference_match_score(article: dict, user_keywords: list, user_sources: list) -> float:
    """
    6️⃣ User Preference Match Score (UPMS)
    Uses embedding-based matching.
    Returns value in [0, 1].
    """
    article_text = (article.get("title", "") + " " + article.get("summary", "")).strip()
    article_url = article.get("url", "")
    
    if not user_keywords and not user_sources:
        return 0.5  # Neutral if no preferences
    
    return user_preference_match_score(article_text, article_url, user_keywords, user_sources)


def compute_engagement_history_score(article_url: str, user_id: int) -> float:
    """
    7️⃣ Engagement History Score (EHS)
    Learn from what the user clicked/bookmarked earlier.
    Returns value in [0, 1].
    """
    if not user_id:
        return 0.5  # Neutral for anonymous users
    
    try:
        with Session(engine) as session:
            # Check if user has clicked this URL before
            click_query = select(ArticleClick).where(
                ArticleClick.user_id == user_id,
                ArticleClick.article_url == article_url
            )
            clicked = session.exec(click_query).first()
            
            if clicked:
                return 1.0  # Maximum score if previously clicked
            
            # Check engagement history for similar domains/topics
            from storage.models import Bookmark
            bookmark_query = select(Bookmark).where(
                Bookmark.user_id == user_id,
                Bookmark.url == article_url
            )
            bookmarked = session.exec(bookmark_query).first()
            
            if bookmarked:
                return 0.9  # High score if bookmarked
            
            # Check for similar domains (weaker signal)
            domain = get_domain_from_url(article_url)
            if domain:
                all_bookmarks = session.exec(
                    select(Bookmark).where(Bookmark.user_id == user_id)
                ).all()
                similar_domains = sum(1 for bm in all_bookmarks if get_domain_from_url(bm.url) == domain)
                if similar_domains > 0:
                    return 0.6  # Moderate boost for similar domains
            
            return 0.5  # Neutral if no engagement history
    except Exception as e:
        print(f"Error computing EHS: {e}")
        return 0.5


def compute_msnrr_score(article: dict, user_id: int = None, user_keywords: list = None, user_sources: list = None) -> float:
    """
    MSNRR: Multi-Signal News Ranking & Relevance Algorithm
    
    Final Ranking Equation:
    MSNRR(article) = 0.2*KMS + 0.15*DAS + 0.15*PS + 0.15*RS + 0.10*SQS + 0.15*UPMS + 0.10*EHS
    
    All components return values in [0, 1].
    """
    article_text = (article.get("title", "") + " " + article.get("summary", "")).strip()
    article_url = article.get("url", "")
    
    # 1️⃣ Keyword Match Score (KMS)
    kms = keyword_match_score(article_text, user_keywords or [])
    
    # 2️⃣ Domain Authority Score (DAS)
    das = compute_domain_authority_score(article_url)
    
    # 3️⃣ Popularity Score (PS)
    ps = compute_popularity_score(article)
    
    # 4️⃣ Recency Score (RS)
    rs = compute_recency_score(article)
    
    # 5️⃣ Summarization Quality Score (SQS)
    summary = article.get("summary", "")
    sqs = compute_summarization_quality_score(summary)
    
    # 6️⃣ User Preference Match Score (UPMS)
    upms = compute_user_preference_match_score(article, user_keywords or [], user_sources or [])
    
    # 7️⃣ Engagement History Score (EHS)
    ehs = compute_engagement_history_score(article_url, user_id) if user_id else 0.5
    
    # Final weighted sum
    msnrr_score = (
        0.2 * kms +
        0.15 * das +
        0.15 * ps +
        0.15 * rs +
        0.10 * sqs +
        0.15 * upms +
        0.10 * ehs
    )
    
    return min(1.0, max(0.0, msnrr_score))


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


def build_digest_items(limit_per_source=8, max_articles=25, user_id: int = None):
    """
    Fetch → extract → summarize → rank with MSNRR → return digest items.
    """
    articles = get_all_articles(limit_per_source=limit_per_source)
    items = []
    
    # Get user preferences if user_id provided
    user_keywords = []
    user_sources = []
    if user_id:
        prefs = get_user_preferences(user_id)
        user_keywords = prefs.get("keywords", [])
        user_sources = prefs.get("sources", [])
    
    # Process articles: extract, summarize, compute MSNRR
    processed_articles = []
    for a in articles:
        title = a.get("title")
        url = a.get("url")
        if not title or not url:
            continue
        
        print(f"Processing: {title}")
        text = extract_article_text(url)
        if not text:
            continue
        if not is_relevant(title, text):
            print("Skipping irrelevant:", title)
            continue

        summary_raw = summarize_text(text)
        
        # Build article dict with all metadata for MSNRR
        article_dict = {
            "title": title,
            "url": url,
            "summary": summary_raw or "",
            "published": a.get("published") or a.get("published_at") or a.get("time"),
            "score": a.get("score", 0),
            "num_comments": a.get("num_comments", 0),
            "upvotes": a.get("upvotes", 0),
            "comments": a.get("comments", 0),
        }
        
        # Compute MSNRR score
        msnrr_score = compute_msnrr_score(
            article_dict,
            user_id=user_id,
            user_keywords=user_keywords,
            user_sources=user_sources
        )
        article_dict["msnrr_score"] = msnrr_score
        processed_articles.append((msnrr_score, article_dict, text, summary_raw))
    
    # Sort by MSNRR score (descending)
    processed_articles.sort(key=lambda x: x[0], reverse=True)
    
    # Process top articles (already extracted, summarized, and scored)
    for msnrr_score, article_dict, text, summary_raw in processed_articles[:max_articles]:
        title = article_dict["title"]
        url = article_dict["url"]

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
            "msnrr_score": round(msnrr_score, 4),  # Include MSNRR score
        }
        items.append(item)
    return items


def save_digest(items):
    """Save latest digest + archive snapshot. File storage is optional for serverless."""
    payload = {"generated_at": int(time.time()), "items": items}
    
    # Try to save to file, but don't fail if file system is read-only
    if FILE_STORAGE_AVAILABLE:
        try:
            with open(LATEST_FILE, "w", encoding="utf8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            
            fname = ARCHIVE_DIR / f"digest_{int(time.time())}.json"
            with open(fname, "w", encoding="utf8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Could not save digest to file (read-only filesystem): {e}")
            # Continue - payload will still be returned and can be stored in database
    else:
        print("File storage not available - digest will only be stored in database")
    
    return payload


def run_full_pipeline(user_id: int = None):
    """Fetch -> summarize -> rank with MSNRR -> save -> return payload"""
    items = build_digest_items(user_id=user_id)
    payload = save_digest(items)
    print(f"Digest built with {len(items)} articles (ranked by MSNRR)")
    return payload

def load_latest_digest():
    """Load latest digest from file if available, otherwise return empty."""
    if FILE_STORAGE_AVAILABLE and LATEST_FILE.exists():
        try:
            with open(LATEST_FILE, "r", encoding="utf8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read digest file: {e}")
            # Fall through to return empty digest
    # Return empty digest if file storage not available or file doesn't exist
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
    """
    Generate personalized digest with MSNRR ranking for the user.
    If digest is stale, regenerate with user context.
    """
    digest = load_latest_digest()
    gen = digest.get("generated_at")
    
    # Check if digest is fresh (less than 1 hour old)
    try:
        freshness = int(os.getenv("DIGEST_FRESHNESS_SECONDS", "3600"))
    except Exception:
        freshness = 3600
    
    # If digest is stale or doesn't exist, regenerate with user context
    if not gen or (time.time() - gen) > freshness:
        print(f"Regenerating digest for user {user_id} with MSNRR ranking...")
        return run_full_pipeline(user_id=user_id)
    
    # Otherwise, filter existing digest by preferences and re-rank by MSNRR
    prefs = get_user_preferences(user_id)
    keywords = prefs.get("keywords", [])
    sources = prefs.get("sources", [])
    match_mode = prefs.get("match_mode", "or")

    items = digest.get("items", [])
    
    # Re-compute MSNRR scores for user context and re-sort
    scored_items = []
    for article in items:
        article_text = (article.get("title", "") + " " + article.get("summary", "")).strip()
        article_dict = {
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "summary": article.get("summary", ""),
            "published": None,  # May not be available in saved digest
            "score": 0,
            "num_comments": 0,
        }
        msnrr_score = compute_msnrr_score(
            article_dict,
            user_id=user_id,
            user_keywords=keywords,
            user_sources=sources
        )
        article["msnrr_score"] = round(msnrr_score, 4)
        scored_items.append((msnrr_score, article))
    
    # Sort by MSNRR score
    scored_items.sort(key=lambda x: x[0], reverse=True)
    ranked_items = [item for _, item in scored_items]
    
    # Apply preference filtering if needed
    if keywords or sources:
        filtered = []
        for article in ranked_items:
            text_blob = " ".join([
                article.get("title", ""),
                " ".join(article.get("bullets", []))
            ]).lower()
            url = article.get("url", "").lower()

            kw_match = any(kw.lower() in text_blob for kw in keywords) if keywords else False
            src_match = any(src.lower() in url for src in sources) if sources else False

            if match_mode == "or":
                if kw_match or src_match:
                    filtered.append(article)
            else:  # AND logic
                if (not keywords or kw_match) and (not sources or src_match):
                    filtered.append(article)
        ranked_items = filtered

    print(f"Personalized digest for user {user_id}: {len(ranked_items)} items (MSNRR-ranked)")

    return {"generated_at": digest.get("generated_at"), "items": ranked_items}
