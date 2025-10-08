import requests


GREENHOUSE_COMPANIES = [
    # FAANG/Big Tech via Greenhouse (some may redirect or be partial)
    "openai", "stripe", "databricks", "snowflake", "airbnb", "uber",
]

LEVER_COMPANIES = [
    # Startups/research orgs on Lever
    "anthropic", "cohere", "runwayml", "perplexity", "stabilityai",
]


def fetch_greenhouse_jobs(companies: list[str] = None, limit: int = 30) -> list[dict]:
    companies = companies or GREENHOUSE_COMPANIES
    articles: list[dict] = []
    for comp in companies:
        try:
            resp = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{comp}/jobs", timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
            jobs = data.get("jobs", [])
            for j in jobs:
                title = j.get("title", "")
                absolute_url = j.get("absolute_url")
                if not absolute_url:
                    continue
                # Prefer internship/entry-level signals
                t_low = title.lower()
                if any(k in t_low for k in ["intern", "internship", "graduate", "new grad", "entry"]):
                    articles.append({"title": f"{title} — {comp.capitalize()} (Greenhouse)", "url": absolute_url})
                elif len(articles) < limit:
                    articles.append({"title": f"{title} — {comp.capitalize()} (Greenhouse)", "url": absolute_url})
                if len(articles) >= limit:
                    break
        except Exception:
            continue
    return articles[:limit]


def fetch_lever_jobs(companies: list[str] = None, limit: int = 30) -> list[dict]:
    companies = companies or LEVER_COMPANIES
    articles: list[dict] = []
    for comp in companies:
        try:
            resp = requests.get(f"https://api.lever.co/v0/postings/{comp}?mode=json", timeout=20)
            if resp.status_code != 200:
                continue
            postings = resp.json() or []
            for p in postings:
                title = p.get("text") or p.get("title") or "Job"
                hosted_url = p.get("hostedUrl") or p.get("applyUrl")
                if not hosted_url:
                    continue
                t_low = title.lower()
                if any(k in t_low for k in ["intern", "internship", "new grad", "graduate", "entry"]):
                    articles.append({"title": f"{title} — {comp.capitalize()} (Lever)", "url": hosted_url})
                elif len(articles) < limit:
                    articles.append({"title": f"{title} — {comp.capitalize()} (Lever)", "url": hosted_url})
                if len(articles) >= limit:
                    break
        except Exception:
            continue
    return articles[:limit]


def fetch_jobs_articles(limit_per_source: int = 30) -> list[dict]:
    articles: list[dict] = []
    try:
        articles.extend(fetch_greenhouse_jobs(limit=limit_per_source))
    except Exception:
        pass
    try:
        articles.extend(fetch_lever_jobs(limit=limit_per_source))
    except Exception:
        pass

    # Dedupe by url
    seen = set()
    unique = []
    for a in articles:
        url = a.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(a)
    return unique


