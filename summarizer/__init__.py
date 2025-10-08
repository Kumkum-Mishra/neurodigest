import os
from .summarizer import summarize_text as summarize_local

GROQ_KEY = os.getenv("GROQ_API_KEY")
if GROQ_KEY:
    from .groq_fallback import summarize_text as summarize_groq
else:
    summarize_groq = None

def summarize_text(text):
    # prefer groq if key present
    if summarize_groq:
        try:
            return summarize_groq(text)
        except Exception as e:
            print("Groq failed, falling back to local:", e)
    return summarize_local(text)
