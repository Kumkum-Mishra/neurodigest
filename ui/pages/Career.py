import streamlit as st
import requests
import datetime
import hashlib


st.set_page_config(page_title="Career Focus • AI Smart News Digest", layout="wide")

API_BASE = "http://localhost:8000"

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

st.title("Career & Company Focus")
st.caption("Internships, placements, roles, salary hints, and company-specific updates")


def _fetch_digest(token: str | None):
    try:
        if token:
            resp = requests.get(
                f"{API_BASE}/api/digest/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=20,
            )
        else:
            resp = requests.get(f"{API_BASE}/api/digest", timeout=20)
        if resp.status_code != 200:
            return {"generated_at": None, "items": [], "_error": f"{resp.status_code} {resp.text}"}
        raw = resp.json()
        if isinstance(raw, dict) and "digest" in raw and isinstance(raw["digest"], dict):
            return raw["digest"]
        return raw
    except Exception as e:
        return {"generated_at": None, "items": [], "_error": str(e)}


act_col1, act_col2 = st.columns([1, 3])
with act_col1:
    if st.button("🔄 Refresh now"):
        try:
            requests.post(f"{API_BASE}/api/trigger", timeout=8)
            st.info("Triggered refresh. Content may update in ~30–45s.")
        except Exception as e:
            st.error(f"Failed to trigger: {e}")

with st.spinner("Loading career-focused items…"):
    data = _fetch_digest(st.session_state.token)

gen = data.get("generated_at")
if gen:
    st.caption("Last generated: " + datetime.datetime.fromtimestamp(gen).strftime("%Y-%m-%d %H:%M:%S"))

items = data.get("items", [])

def _domain_from_url(url: str) -> str:
    try:
        return url.split("//", 1)[-1].split("/", 1)[0].replace("www.", "").lower()
    except Exception:
        return ""

def _is_career(it: dict) -> bool:
    text = (it.get("title", "") + " " + " ".join(it.get("bullets", []))).lower()
    if any(k in text for k in ["hiring", "intern", "internship", "placement", "career", "resume", "offer", "salary", "role"]):
        return True
    # also include items enriched with role/salary/company signals
    if it.get("role") or it.get("salary_hint"):
        return True
    return False

# Merge career and company focus (both signals)
def _is_company_focus(it: dict) -> bool:
    return bool((it.get("company") or "").strip())

career_items = [it for it in items if _is_career(it) or _is_company_focus(it)]

# Styling (match Dashboard style)
st.markdown(
    """
    <style>
    .digest-card {border-radius: 16px; padding: 20px; margin-bottom: 20px; border: 2px solid transparent; background: linear-gradient(135deg, #f8fafc, #e2e8f0); box-shadow: 0 4px 20px rgba(0,0,0,0.1); color: #1e293b; transition: all 0.3s ease;} 
    .digest-card:hover {transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.15);} 
    .digest-title {font-size: 1.2rem; font-weight: 800; margin-bottom: 8px; color: #0f172a; background: linear-gradient(135deg, #22c55e, #16a34a); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
    .digest-meta {font-size: 0.9rem; color: #64748b; margin-bottom: 12px; display:flex; align-items:center; gap:10px;}
    .badge {display: inline-block; background: linear-gradient(135deg, #22c55e, #16a34a); color: #ffffff; border-radius: 20px; padding: 4px 12px; font-size: 11px; margin-right: 8px; font-weight: 600; box-shadow: 0 2px 8px rgba(34,197,94,0.3);}    
    .logo {width: 18px; height: 18px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.15);} 
    .bullet {margin-left: 0; padding-left: 20px; color: #475569;} 
    .bullet li {margin: 6px 0; position: relative;} 
    .bullet li:before {content: "▶"; color: #22c55e; font-weight: bold; position: absolute; left: -15px;} 
    .digest-card a { color: #16a34a !important; text-decoration: none; font-weight: 600; } 
    .digest-card a:hover { text-decoration: underline; color: #15803d !important; } 
    </style>
    """,
    unsafe_allow_html=True,
)


def render_card(it: dict, key_prefix: str):
    title = it.get("title") or "Untitled"
    url = it.get("url")
    dom = _domain_from_url(url or "")
    bullets = it.get("bullets", [])
    if not bullets:
        summary_text = (it.get("summary", "") or "").replace("\r", " ").replace("\n", " ")
        if summary_text:
            bullets = [s.strip().rstrip(" .") for s in summary_text.split(". ") if s.strip()][:4]
    if not bullets:
        bullets = ["Summary not available. Click the link to read more."]

    chips = []
    if it.get("company"):
        chips.append(f"<span class='badge'>🏢 {it['company']}</span>")
    if it.get("role"):
        chips.append(f"<span class='badge'>💼 {it['role']}</span>")
    if it.get("salary_hint"):
        chips.append(f"<span class='badge'>💰 {it['salary_hint']}</span>")

    bullet_html = "".join([f"<li>{b}</li>" for b in bullets])
    link_html = f"<a href='{url}' target='_blank'>Read original</a>" if url else ""
    dom_html = f"<span class='badge'>{dom}</span>" if dom else ""
    logo_html = f"<img class='logo' src='https://www.google.com/s2/favicons?domain={dom}&sz=64' alt='logo'/>" if dom else ""
    tag_badges = " ".join(chips)

    st.markdown(
        f"""
        <div class='digest-card'>
          <div class='digest-title'>{title}</div>
          <div class='digest-meta'>{logo_html} {dom_html} {tag_badges} {link_html}</div>
          <ul class='bullet'>{bullet_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


if not career_items:
    st.warning("No career-focused items yet. Try refreshing or adjust your preferences.")
else:
    for idx, it in enumerate(career_items):
        render_card(it, key_prefix=f"career_{idx}")


