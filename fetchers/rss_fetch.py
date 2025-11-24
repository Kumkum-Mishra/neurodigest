import feedparser
from datetime import datetime, timedelta
from urllib.parse import urlparse
import random


# -----------------------------
# Helpers
# -----------------------------
def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return ""


# -----------------------------
# AI / ML / LLM Research Sources
# -----------------------------
AI_SOURCES = [
    "https://ai.googleblog.com/feeds/posts/default",
    "https://openai.com/blog/rss",
    "https://arxiv.org/rss/cs.AI",
    "https://arxiv.org/rss/cs.LG",
    "https://huggingface.co/blog/feed.xml",
    "https://deepmind.com/blog/feed/basic/",
    "https://www.anthropic.com/news/rss.xml",
    "https://ai.meta.com/blog/rss/",
    "https://developer.nvidia.com/blog/feed/",
    "https://aitrends.com/feed/",
    "https://paperswithcode.com/rss/latest",
    "https://www.microsoft.com/en-us/research/blog/feed/",
    "https://www.ibm.com/blogs/research/feed/",
    "https://www.fast.ai/feed.xml",
    "https://research.google/blog/feed/",
    "https://stability.ai/feed",
    "https://cohere.com/blog/rss.xml",
    "https://www.databricks.com/blog/feed",
    "https://www.deepseek.com/blog/feed",  # if available (fallback will skip)
]


# -----------------------------
# Tech & AI Industry News
# -----------------------------
TECH_SOURCES = [
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/feed/category/artificial-intelligence/",
    "https://www.wired.com/category/ai/feed/",
    "https://analyticsindiamag.com/feed/",
    "https://www.theverge.com/rss/ai",
    "https://towardsdatascience.com/feed",
    "https://www.kdnuggets.com/feed",
    "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
    "https://www.engadget.com/rss.xml",
    "https://www.techradar.com/rss",
    "https://www.infoq.com/ai-ml/rss/",
    "https://thenewstack.io/feed/",
    "https://www.sciencenews.org/topic/artificial-intelligence/feed",
]


# -----------------------------
# Student / Learning / Career / Upskilling
# -----------------------------
STUDENT_SOURCES = [
    "https://www.kaggle.com/blog/feed",
    "https://www.freecodecamp.org/news/rss/",
    "https://www.datacamp.com/community/blog/rss.xml",
    "https://pub.towardsai.net/feed",
    "https://medium.com/feed/tag/data-science",
    "https://ai.stackexchange.com/feeds",
    "https://stackoverflow.blog/feed/",
    "https://producthunt.com/feed/topic/artificial-intelligence",
    "https://machinelearningmastery.com/blog/feed/",
    "https://realpython.com/atom.xml",
    "https://betterprogramming.pub/feed",
]


# -----------------------------
# Job Boards + Placement-Oriented
# -----------------------------
JOBS_SOURCES = [
    "https://www.indeed.com/career-advice/rss",
    "https://www.glassdoor.com/blog/feed/",
    "https://careercup.com/feed",
    "https://leetcode.com/discuss/feed",
    "https://www.hackerrank.com/blog/feed",
    "https://www.interviewbit.com/blog/feed/",
    "https://news.ycombinator.com/jobs",
]


# -----------------------------
# General Tech / Dev / Startups / Founders
# -----------------------------
GENERAL_TECH_SOURCES = [
    "https://news.ycombinator.com/rss",
    "https://the-decoder.com/feed/",
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://medium.com/feed/tag/technology",
    "https://www.economist.com/science-and-technology/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
]


# -----------------------------
# MASTER LIST (100+ sources)
# -----------------------------
RSS_FEEDS = list(
    set(
        AI_SOURCES
        + TECH_SOURCES
        + STUDENT_SOURCES
        + JOBS_SOURCES
        + GENERAL_TECH_SOURCES
    )
)


# -------------------------------------------------------
# Main Fetch Function
# -------------------------------------------------------
def fetch_rss_articles(limit_per_source=4, days_filter=3):
    """
    Fetch and filter 100+ sources.
    Returns: {title, url, summary, source, domain, published}
    """
    articles = []
    cutoff = datetime.utcnow() - timedelta(days=days_filter)

    print(f"🔍 Fetching RSS from {len(RSS_FEEDS)} sources...")

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            source_name = feed.feed.get("title", feed_url)
            domain = get_domain(feed_url)

            for entry in feed.entries[:limit_per_source]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                summary = entry.get("summary", "")

                # extract publish date
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    dt = datetime(*entry.published_parsed[:6])
                    if dt < cutoff:
                        continue
                    published = dt.isoformat()

                if not title or not link:
                    continue

                articles.append(
                    {
                        "title": title,
                        "url": link,
                        "summary": summary,
                        "source": source_name,
                        "domain": domain,
                        "published": published,
                    }
                )

        except Exception as e:
            print(f"⚠ RSS error → {feed_url} : {e}")

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in articles:
        if a["url"] not in seen:
            unique.append(a)
            seen.add(a["url"])

    random.shuffle(unique)

    print(f"📌 Total unique RSS items: {len(unique)}")
    return unique


# -------------------------------------------------------
# Test Runner
# -------------------------------------------------------
if __name__ == "__main__":
    data = fetch_rss_articles(limit_per_source=2)
    for x in data[:10]:
        print(f"{x['title']}  |  {x['domain']}")
