import requests

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
    headers = {"User-Agent": "Mozilla/5.0"}
    articles = []

    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
        res = requests.get(url, headers=headers)
        posts = res.json().get("data", {}).get("children", [])
        for post in posts:
            data = post["data"]
            if data.get("url"):
                articles.append({"title": data["title"], "url": data["url"]})

    return articles
