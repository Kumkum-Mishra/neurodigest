import feedparser

RSS_FEEDS = [
    # AI / Tech trends
    "https://the-decoder.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://www.technologyreview.com/feed/category/artificial-intelligence/",
    "https://techcrunch.com/feed/",  # broader tech trends

    # Student placement and interview prep blogs
    "https://www.geeksforgeeks.org/feed/",
    "https://www.interviewbit.com/blog/feed/",
    "https://www.hackerrank.com/blog/feed/",
    "https://leetcode.com/discuss/feed",  # community discussions
    "https://www.glassdoor.com/blog/feed/",
    "https://www.indeed.com/career-advice/rss",
    "https://careercup.com/feed",
    "https://medium.com/feed/tag/interview-preparation",
    "https://stackoverflow.blog/feed/",
    "https://news.ycombinator.com/rss",

    # ArXiv AI/ML research (high-level titles helpful for trend awareness)
    "http://export.arxiv.org/rss/cs.AI",
    "http://export.arxiv.org/rss/cs.LG",

    # Company job boards via RSS-like endpoints (some may be partial)
    # Note: many modern job boards require APIs; these are placeholders for public feeds
    "https://boards.greenhouse.io/blog.atom",  # Greenhouse blog (jobs insights)
    "https://lever.co/blog/feed/",            # Lever blog (hiring insights)
]

def fetch_rss_articles(limit=5):
    articles = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:limit]:
            articles.append({"title": entry.title, "url": entry.link})
    return articles
