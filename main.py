# === Import all modules ===
from fetchers.hn_fetch import fetch_hn_articles
from fetchers.reddit_fetch import fetch_reddit_articles
from fetchers.rss_fetch import fetch_rss_articles

from extract_content import extract_article_text
from summarizer.summarizer import summarize_text
from delivery.emailer import send_email

# === Email credentials ===
from_email = "kumkummishra892004@gmail.com"
to_email = "kumkum.loves.dance@gmail.com"
email_password = "fbgv cpgm xzob suoa"

# === Relevant keywords for filtering ===
KEYWORDS = [
    "ai", "machine learning", "openai", "deepseek", "google", "gemini",
    "perplexity", "gen ai", "llm", "mnc", "btech", "india", "research",
    "deep learning", "startup", "model", "launch", "github", "microsoft",
    "python", "tech", "release", "innovation", "founder", "hiring", "interview"
]

# === Utility: Check if an article is relevant ===
def is_relevant(title: str, content: str) -> bool:
    full_text = (title + " " + content).lower()
    return any(keyword in full_text for keyword in KEYWORDS)

# === Utility: Format summary into simple bullet points ===
def format_bullets(summary_text):
    lines = summary_text.strip().split(". ")
    bullets = [f"{line.strip().rstrip('.')}" for line in lines if len(line.strip()) > 10]
    return "\n".join(bullets[:4])  # Max 4 bullets

# === Combine news from all sources ===
def get_all_articles():
    articles = []
    articles.extend(fetch_hn_articles(limit=5))
    articles.extend(fetch_reddit_articles(limit=5))
    articles.extend(fetch_rss_articles(limit=5))
    return articles

# === Build the daily digest ===
def build_digest():
    articles = get_all_articles()
    digest = []

    for article in articles:
        print(f"\nProcessing: {article['title']}")
        try:
            content = extract_article_text(article['url'])
        except Exception as e:
            print(f"Failed to extract: {e}")
            continue

        if not is_relevant(article['title'], content):
            print("⏭ Skipping (not AI/tech relevant).")
            continue

        try:
            summary = summarize_text(content)
            bullets = format_bullets(summary)
            formatted = f"{article['title']}\n{article['url']}\n{bullets}\n"
            digest.append(formatted)
        except Exception as e:
            print(f"Failed to summarize: {e}")
            continue

    return "\n\n".join(digest)

# === Run the pipeline ===
if __name__ == "__main__":
    digest = build_digest()

    if digest:
        send_email(
            subject="Your Curated Daily AI Digest",
            body=digest,
            to_email=to_email,
            from_email=from_email,
            password=email_password
        )
        print("\nDigest sent successfully!")
    else:
        print("\nNo relevant articles found today.")



"""# Import all modules
from hn_fetch import fetch_top_hn_articles
from extract_content import extract_article_text
from summarizer import summarize_text
from emailer import send_email

# Your credentials
from_email = "kumkummishra892004@gmail.com"
to_email = "kumkum.loves.dance@gmail.com"
email_password = "fbgv cpgm xzob suoa"

# Define keywords to keep only relevant articles
KEYWORDS = ["ai", "machine learning", "openai", "deepseek","google", "gemini", "perplexity", "Gen AI", "LLM", "MNC", "Btech", "India", "Research", "deep learning" "startup", "model", "launch", "github", "microsoft", "python", "tech", "release"]

# Utility function to check article relevance
def is_relevant(title: str, content: str) -> bool:
    full_text = (title + " " + content).lower()
    return any(keyword in full_text for keyword in KEYWORDS)

# Format summary as bullet points
def format_bullets(summary_text):
    lines = summary_text.strip().split(". ")
    bullets = [f"- {line.strip()}" for line in lines if len(line.strip()) > 10]
    return "\n".join(bullets[:4])  # Max 4 bullets

# Build digest with filtered and bullet-formatted articles
def build_digest():
    articles = fetch_top_hn_articles()
    digest = []

    for article in articles:
        print(f"Processing: {article['title']}")
        content = extract_article_text(article['url'])

        if not is_relevant(article['title'], content):
            print("⏭Skipping irrelevant article.")
            continue

        summary = summarize_text(content)
        bullets = format_bullets(summary)
        formatted = f"{article['title']}\n{article['url']}\n{bullets}\n"
        digest.append(formatted)

    return "\n\n".join(digest)

# Main entry
if __name__ == "__main__":
    digest = build_digest()
    if digest:
        send_email("Your Filtered Daily Tech Digest", digest, to_email, from_email, email_password)
        print("Digest sent successfully!")
    else:
        print("No relevant articles found.")"""
