import requests

def fetch_hn_articles(limit=10):
    sources = ["topstories", "newstories", "beststories"]  # More variety
    seen = set()
    articles = []

    for source in sources:
        ids = requests.get(f"https://hacker-news.firebaseio.com/v0/{source}.json").json()
        for story_id in ids:
            if story_id in seen:
                continue
            seen.add(story_id)
            data = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
            if data and 'url' in data:
                articles.append({'title': data['title'], 'url': data['url']})
            if len(articles) >= limit:
                break
        if len(articles) >= limit:
            break

    return articles


def fetch_hn_jobs(limit=10):
    ids = requests.get("https://hacker-news.firebaseio.com/v0/jobstories.json").json()
    articles = []
    for story_id in ids[:limit]:
        data = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
        if data and 'url' in data:
            articles.append({'title': data['title'], 'url': data['url']})
    return articles


"""import feedparser

def fetch_top_ai_articles(limit=8):
    rss_feeds = [
        # Google News: AI
        "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en",

        # VentureBeat AI section
        "https://venturebeat.com/category/ai/feed/",

        # MIT Technology Review AI section
        "https://www.technologyreview.com/feed/category/artificial-intelligence/"
    ]

    keywords = ["AI", "artificial intelligence", "machine learning", "ChatGPT", "OpenAI", "DeepMind", "Anthropic", "Neuralink"]

    articles = []

    for feed_url in rss_feeds:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            title = entry.title
            link = entry.link

            if any(keyword.lower() in title.lower() for keyword in keywords):
                articles.append({'title': title, 'url': link})

            if len(articles) >= limit:
                return articles  # Early return when limit is reached

    return articles"""





"""import requests

def fetch_top_hn_articles(limit=5):
    top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
    articles = []

    for story_id in top_ids[:limit]:
        url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        data = requests.get(url).json()
        if data and 'url' in data:
            articles.append({'title': data['title'], 'url': data['url']})

    return articles"""
