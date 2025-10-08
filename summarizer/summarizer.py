import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL")

def summarize_text(text, use_groq=True, model="llama-3.1-8b-instant"):
    """
    Summarize text using Groq API (default) or Ollama fallback.
    """
    if use_groq and GROQ_API_KEY:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Summarize news into 3-4 short, clear bullet points. Avoid jargon."},
                {"role": "user", "content": text[:3000]},
            ],
            "temperature": 0.3,
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            print("🔹 Sent request to Groq")
            print("🔹 Response status:", response.status_code)
            print("🔹 Response text:", response.text[:500])  # print first 500 chars

            if response.status_code == 200:
                try:
                   data = response.json()
                   content = data["choices"][0]["message"]["content"].strip()
                   return content if content else "No summary returned from Groq."
                except Exception as parse_err:
                    print("❌ Failed to parse Groq response:", parse_err)
                    print("🔹 Raw response:", response.text[:500])
                    return "No summary available (Groq parsing error)."
            else:
                print("❌ Groq error:", response.status_code, response.text[:500])
                return "No summary available (Groq error)."

        except Exception as e:
            print("❌ Groq summarizer failed:", str(e))
            return "No summary available."

    elif OLLAMA_URL:
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "phi3", "prompt": text[:3000], "stream": False}
            )
            print("🔹 Using Ollama fallback")
            return response.json().get("response", "No summary available (Ollama).")
        except Exception as e:
            print("❌ Ollama summarizer failed:", str(e))
            return "No summary available."

    else:
        return "No summarizer available. Please set GROQ_API_KEY or OLLAMA_URL."
