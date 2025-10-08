# summarizer/groq_fallback.py
import os, requests
from dotenv import load_dotenv
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

def summarize_text(text, model="llama3-8b-8192"):
    prompt = (
        "Summarize the following news article into 3 short, simple bullet points:\n"
        "- Use plain language for both tech and non-tech readers\n"
        "- Focus on what happened, why it matters, and any impact\n\n"
        f"Article:\n{text[:3000]}"
    )
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # adapt this depending on API response structure
    return data["choices"][0]["message"]["content"].strip()
