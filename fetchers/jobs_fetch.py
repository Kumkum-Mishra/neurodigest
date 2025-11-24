import requests
from urllib.parse import urlparse

def get_domain(url): 
    try: return urlparse(url).netloc.replace("www.", "") 
    except: return ""

GREENHOUSE_COMPANIES = ["openai", "stripe", "databricks"]
LEVER_COMPANIES = ["anthropic", "cohere", "runwayml"]

def fetch_greenhouse_jobs(companies=None, limit=30):
    companies = companies or GREENHOUSE_COMPANIES
    out = []

    for comp in companies:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{comp}/jobs"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue

            for j in resp.json().get("jobs", []):
                link = j.get("absolute_url")
                if not link:
                    continue

                title = j.get("title", "Job")
                out.append({
                    "title": f"{title} — {comp}",
                    "url": link,
                    "domain": get_domain(link),
                    "source": comp,
                    "summary": "",
                    "published": None
                })

                if len(out) >= limit:
                    break
        except:
            pass

    return out[:limit]


def fetch_lever_jobs(companies=None, limit=30):
    companies = companies or LEVER_COMPANIES
    out = []

    for comp in companies:
        try:
            url = f"https://api.lever.co/v0/postings/{comp}?mode=json"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                continue

            for p in resp.json():
                link = p.get("hostedUrl") or p.get("applyUrl")
                if not link:
                    continue

                title = p.get("text") or p.get("title") or "Job"
                out.append({
                    "title": f"{title} — {comp}",
                    "url": link,
                    "domain": get_domain(link),
                    "source": comp,
                    "summary": "",
                    "published": None
                })

                if len(out) >= limit:
                    break
        except:
            pass

    return out[:limit]


def fetch_jobs_articles(limit_per_source=30):
    all_jobs = []

    try: all_jobs += fetch_greenhouse_jobs(limit=limit_per_source)
    except: pass

    try: all_jobs += fetch_lever_jobs(limit=limit_per_source)
    except: pass

    # dedupe
    seen = set()
    unique = []
    for a in all_jobs:
        if a["url"] not in seen:
            unique.append(a)
            seen.add(a["url"])

    return unique
