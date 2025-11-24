import requests
from urllib.parse import urlparse

TIMEOUT = 8


def get_domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""


# -------------------------------------------------------------
# Hacker News: Top / New / Best stories
# -------------------------------------------------------------
def fetch_hn_articles(limit=10):
    sources = ["topstories", "newstories", "beststories"]
    out = []
    seen = set()

    for src in sources:
        try:
            ids = requests.get(
                f"https://hacker-news.firebaseio.com/v0/{src}.json",
                timeout=TIMEOUT
            ).json()

            for story_id in ids:
                if story_id in seen:
                    continue
                seen.add(story_id)

                data = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=TIMEOUT
                ).json()

                if data and "url" in data:
                    url = data["url"]
                    out.append({
                        "title": data.get("title", "HN Story"),
                        "url": url,
                        "domain": get_domain(url),
                        "source": "Hacker News",
                        "summary": "",
                        "published": data.get("time"),  # Unix timestamp
                        "score": data.get("score", 0),  # Upvotes
                        "num_comments": data.get("descendants", 0),  # HN uses "descendants"
                        "upvotes": data.get("score", 0),
                        "comments": data.get("descendants", 0),
                    })

                if len(out) >= limit:
                    return out

        except Exception:
            continue

    return out


# -------------------------------------------------------------
# Hacker News Job Posts
# -------------------------------------------------------------
def fetch_hn_jobs(limit=10):
    """Fetch job listings from HN jobstories (internships, full-time posts)."""
    try:
        ids = requests.get(
            "https://hacker-news.firebaseio.com/v0/jobstories.json",
            timeout=TIMEOUT
        ).json()
    except Exception:
        return []

    out = []
    for story_id in ids[:limit]:
        try:
            data = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                timeout=TIMEOUT
            ).json()

            if data and "url" in data:
                url = data["url"]
                out.append({
                    "title": data.get("title", "HN Job"),
                    "url": url,
                    "domain": get_domain(url),
                    "source": "Hacker News Jobs",
                    "summary": "",
                    "published": data.get("time"),  # Unix timestamp
                    "score": 0,  # Jobs typically don't have scores
                    "num_comments": 0,
                    "upvotes": 0,
                    "comments": 0,
                })

        except Exception:
            continue

    return out
