import requests
from urllib.parse import urlparse

def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""

def fetch_reddit_articles(
    subreddits=[
        "csinterviewproblems",  # interview questions
        "leetcode",             # DSA trends
        "cscareerquestions",    # placement/career insights
        "Internships",          # internships worldwide
        "Artificial",
        "MachineLearning",
        "OpenAI",
        "programming",          # general dev trends
        "datascience",
        "computerscience",
    ],
    limit=5,
):
    headers = {"User-Agent": "Mozilla/5.0 AI-NewsDigest Bot"}
    articles = []

    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
            res = requests.get(url, headers=headers, timeout=8)

            if res.status_code != 200:
                continue

            posts = res.json().get("data", {}).get("children", [])
            for post in posts:
                data = post["data"]
                link = data.get("url")

                if not link:
                    continue

                articles.append({
                    "title": data["title"],
                    "url": link,
                    "source": f"r/{sub}",
                    "domain": get_domain(link),
                    "summary": "",
                    "published": data.get("created_utc"),  # Unix timestamp
                    "score": data.get("score", 0),  # Upvotes
                    "num_comments": data.get("num_comments", 0),
                    "upvotes": data.get("score", 0),
                    "comments": data.get("num_comments", 0),
                })
        except:
            continue

    return articles

