import os
import time
import requests


API_BASE = os.getenv("API_BASE", "http://localhost:8000")
TOKEN = os.getenv("API_TOKEN")  # optional: set a JWT to test personalized digest


def fetch_digest(token: str | None):
    try:
        if token:
            r = requests.get(
                f"{API_BASE}/api/digest/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
        else:
            r = requests.get(f"{API_BASE}/api/digest", timeout=15)
        r.raise_for_status()
        raw = r.json()
        if isinstance(raw, dict) and "digest" in raw and isinstance(raw["digest"], dict):
            return raw["digest"]
        return raw
    except Exception as e:
        return {"generated_at": None, "items": [], "_error": str(e)}


def trigger_build():
    r = requests.post(f"{API_BASE}/api/trigger", timeout=10)
    r.raise_for_status()
    return r.json()


def main():
    print(f"Using API_BASE={API_BASE}")
    digest = fetch_digest(TOKEN)
    baseline = digest.get("generated_at")
    print("Current generated_at:", baseline)

    print("Triggering build...")
    out = trigger_build()
    print("Trigger response:", out)

    print("Polling for updated digest (max 60s)...")
    start = time.time()
    while time.time() - start < 60:
        updated = fetch_digest(TOKEN)
        new_gen = updated.get("generated_at")
        if new_gen and new_gen != baseline and updated.get("items"):
            print("New digest detected!:", new_gen)
            print("Items:", len(updated.get("items", [])))
            print("Sample title:", updated.get("items", [{}])[0].get("title"))
            return 0
        time.sleep(3)

    print("Timed out waiting for an updated digest. Try again or check logs.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

