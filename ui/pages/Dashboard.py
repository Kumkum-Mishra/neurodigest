import streamlit as st
import requests
import datetime
import hashlib
import re


st.set_page_config(page_title="Dashboard • Campus Placement Digest", layout="wide")

API_BASE = "http://localhost:8000"

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

st.title("Dashboard")
if not st.session_state.token:
    st.info("You are not logged in. Please go to Login page.")

def _fetch_digest(token: str | None):
    try:
        if token:
            resp = requests.get(
                f"{API_BASE}/api/digest/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
        else:
            resp = requests.get(f"{API_BASE}/api/digest", timeout=15)
        if resp.status_code != 200:
            return {"generated_at": None, "items": [], "_error": f"{resp.status_code} {resp.text}"}
        raw = resp.json()
        if isinstance(raw, dict) and "digest" in raw and isinstance(raw["digest"], dict):
            return raw["digest"]
        return raw
    except Exception as e:
        return {"generated_at": None, "items": [], "_error": str(e)}


# Use a simple session_state-backed cache to avoid refetching the digest on
# every navigation/rerun. This mirrors the helper used in the landing/Tutor UI.
def _cached_get_digest(token: str | None, state_key: str = "_dashboard_digest", ttl: int = 120, force: bool = False):
    import time
    now = int(time.time())
    ts_key = f"{state_key}_ts"
    if not force and st.session_state.get(state_key) is not None and st.session_state.get(ts_key) is not None:
        if now - int(st.session_state.get(ts_key, 0)) < ttl:
            return st.session_state.get(state_key)

    # perform a fresh fetch
    try:
        if token:
            resp = requests.get(
                f"{API_BASE}/api/digest/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
        else:
            resp = requests.get(f"{API_BASE}/api/digest", timeout=15)
        if resp.status_code != 200:
            return {"generated_at": None, "items": [], "_error": f"{resp.status_code} {resp.text}"}
        raw = resp.json()
        if isinstance(raw, dict) and "digest" in raw and isinstance(raw["digest"], dict):
            payload = raw["digest"]
        else:
            payload = raw
        st.session_state[state_key] = payload
        st.session_state[ts_key] = now
        return payload
    except Exception as e:
        # fall back to cached value if available
        return st.session_state.get(state_key, {"generated_at": None, "items": [], "_error": str(e)})

col_main, col_actions = st.columns([3, 1])

with col_actions:
    if st.button("🔄 Refresh now", key="refresh_btn"):
        # Perform a synchronous refresh but store in the cache so subsequent
        # navigations read the cached value instead of re-fetching.
        try:
            with st.spinner("Refreshing digest... this may take up to 60s"):
                resp = requests.get(f"{API_BASE}/api/digest?refresh=1", timeout=120)
                if resp.status_code == 200:
                    payload = resp.json()
                    if isinstance(payload, dict) and "digest" in payload and isinstance(payload["digest"], dict):
                        st.session_state["_dashboard_digest"] = payload["digest"]
                    else:
                        st.session_state["_dashboard_digest"] = payload
                    st.session_state["_dashboard_digest_ts"] = int(time.time())
                    st.success("Digest refreshed")
                    st.experimental_rerun()
                else:
                    st.error(f"Failed to refresh digest: {resp.status_code} {resp.text}")
        except Exception as e:
            st.error("Failed to refresh: " + str(e))

with st.spinner("Fetching digest..."):
    # prefer any manual-refresh result placed in session_state, otherwise use cached getter
    data = st.session_state.pop("_latest_digest", None) or _cached_get_digest(st.session_state.token)

gen = data.get("generated_at")
if gen:
    st.caption("Last generated: " + datetime.datetime.fromtimestamp(gen).strftime("%Y-%m-%d %H:%M:%S"))

items = data.get("items", [])
error_msg = data.get("_error")
if error_msg:
    st.error(f"Failed to fetch digest: {error_msg}")
    # Offer an inline retry that uses the same refresh endpoint
    if st.button("Retry fetching digest"):
        try:
            with st.spinner("Refreshing digest... this may take up to 60s"):
                resp = requests.get(f"{API_BASE}/api/digest?refresh=1", timeout=120)
                if resp.status_code == 200:
                    payload = resp.json()
                    if isinstance(payload, dict) and "digest" in payload and isinstance(payload["digest"], dict):
                        st.session_state["_latest_digest"] = payload["digest"]
                    else:
                        st.session_state["_latest_digest"] = payload
                    st.success("Digest refreshed — reloading")
                    _ = st.experimental_rerun()
                else:
                    st.error(f"Failed to refresh digest: {resp.status_code} {resp.text}")
        except Exception as e:
            st.error(f"Failed to refresh: {e}")

# Fetch user's bookmarks to enable save/remove and filtering
saved_url_to_id: dict[str, int] = {}
user_keywords: list[str] = []
user_sources: list[str] = []
user_match_mode: str = "or"
if st.session_state.token:
    try:
        r_bm = requests.get(
            f"{API_BASE}/user/bookmarks",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10,
        )
        if r_bm.status_code == 200:
            for row in r_bm.json():
                if row.get("url"):
                    saved_url_to_id[row["url"]] = row.get("id")
    except Exception:
        pass
    # fetch preferences to compute For You matching
    try:
        r_prefs = requests.get(
            f"{API_BASE}/prefs/me",
            headers={"Authorization": f"Bearer {st.session_state.token}"},
            timeout=10,
        )
        if r_prefs.status_code == 200:
            prefs = r_prefs.json()
            user_keywords = [s.strip().lower() for s in (prefs.get("keywords") or "").split(",") if s.strip()]
            user_sources = [s.strip().lower() for s in (prefs.get("sources") or "").split(",") if s.strip()]
            user_match_mode = (prefs.get("match_mode") or "or").lower()
    except Exception:
        pass

def _domain_from_url(url: str) -> str:
    try:
        return url.split("//", 1)[-1].split("/", 1)[0].replace("www.", "").lower()
    except Exception:
        return ""

def _categorize(it: dict) -> str:
    text = (it.get("title", "") + " " + " ".join(it.get("bullets", []))).lower()
    if any(k in text for k in ["interview", "dsa", "system design", "leetcode", "hackerrank", "geeksforgeeks"]):
        return "Interviews / DSA"
    if any(k in text for k in ["ai", "llm", "machine learning", "deep learning", "arxiv", "research", "chatgpt", "gemini"]):
        return "AI Trends"
    if any(k in text for k in ["hiring", "internship", "placement", "career", "resume", "offer"]):
        return "Career"
    return "For You"


def strip_ai_intro(text: str) -> str:
    """Remove common AI-generated intro lines like
    'Here are 4 short, clear bullet points to help you ace an internship interview:'
    so the frontend doesn't display obvious AI-prefacing lines.
    """
    if not text:
        return text

    s = text.lstrip()
    # Simple, robust approach: if the string starts with "Here are" (case-insensitive)
    # and contains a ':' later, check whether the prefix mentions "bullet point" or
    # "to help you"; if so, strip the prefix up to the colon.
    low = s.lower()
    if low.startswith("here are"):
        colon_idx = s.find(":")
        if colon_idx != -1:
            prefix = s[:colon_idx+1].lower()
            if "bullet point" in prefix or "to help you" in prefix:
                return s[colon_idx+1:].lstrip()

    # fallback: also handle cases where the phrase appears at the start without a colon
    # e.g. "Here are 4 short clear bullet points to help you ace..."
    if low.startswith("here are") and ("bullet point" in low or "to help you" in low):
        # try to remove the leading clause up to the first full sentence end or first dash
        for sep in [". ", "\n", " - "]:
            idx = s.find(sep)
            if idx != -1 and idx < 140:
                return s[idx+len(sep):].lstrip()
        # if nothing found, remove the first 120 chars as a last resort
        return s[120:].lstrip() if len(s) > 120 else ""

    return text

# Sidebar filters
domains = sorted({_domain_from_url(it.get("url", "")) for it in items if it.get("url")})
selected_domains = st.sidebar.multiselect("Filter by source (domain)", options=[d for d in domains if d], default=[])
show_only_saved = st.sidebar.checkbox("Show only saved (bookmarked)", value=False)
search_query = st.sidebar.text_input("Search in titles/summaries", "")

def _passes_filters(it: dict) -> bool:
    text = (it.get("title", "") + " " + " ".join(it.get("bullets", []))).lower()
    if search_query and search_query.lower() not in text:
        return False
    if selected_domains:
        d = _domain_from_url(it.get("url", ""))
        if d not in selected_domains:
            return False
    if show_only_saved:
        if it.get("url") not in saved_url_to_id:
            return False
    return True

filtered = [it for it in items if _passes_filters(it)]
sections = {"For You": [], "All News (24h)": [], "Interviews / DSA": [], "AI Trends": [], "Career": []}

def _user_pref_match(it: dict) -> bool:
    if not (user_keywords or user_sources):
        return False
    text = (it.get("title", "") + " " + " ".join(it.get("bullets", []))).lower()
    url = (it.get("url") or "").lower()
    kw_match = any(k in text for k in user_keywords) if user_keywords else False
    src_match = any(s in url for s in user_sources) if user_sources else False
    if user_match_mode == "and":
        return (not user_keywords or kw_match) and (not user_sources or src_match)
    return kw_match or src_match

for it in filtered:
    cat = _categorize(it)
    if cat != "For You":
        sections[cat].append(it)
    # For You contains only preference-matching items (personalized)
    if _user_pref_match(it):
        sections["For You"].append(it)
    sections["All News (24h)"].append(it)

# Styling
st.markdown(
    """
    <style>
    .digest-card {border-radius: 16px; padding: 20px; margin-bottom: 20px; border: 2px solid transparent; background: linear-gradient(135deg, #f8fafc, #e2e8f0); box-shadow: 0 4px 20px rgba(0,0,0,0.1); color: #1e293b; transition: all 0.3s ease;} 
    .digest-card:hover {transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.15);}
    .digest-title {font-size: 1.2rem; font-weight: 800; margin-bottom: 8px; color: #0f172a; background: linear-gradient(135deg, #3b82f6, #1d4ed8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
    .digest-meta {font-size: 0.9rem; color: #64748b; margin-bottom: 12px; display:flex; align-items:center; gap:10px;}
    .logo {width: 18px; height: 18px; border-radius: 4px; box-shadow: 0 1px 4px rgba(0,0,0,0.15);}
    .badge {display: inline-block; background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: #ffffff; border-radius: 20px; padding: 4px 12px; font-size: 11px; margin-right: 8px; font-weight: 600; box-shadow: 0 2px 8px rgba(59,130,246,0.3);}
    .bullet {margin-left: 0; padding-left: 20px; color: #475569;}
    .bullet li {margin: 6px 0; position: relative;}
    .bullet li:before {content: "▶"; color: #3b82f6; font-weight: bold; position: absolute; left: -15px;}
    .digest-card a { color: #1d4ed8 !important; text-decoration: none; font-weight: 600; }
    .digest-card a:hover { text-decoration: underline; color: #1e40af !important; }
    .section-header {font-size: 1.3rem; font-weight: 900; margin: 12px 0 8px 0; background: linear-gradient(135deg, #3b82f6, #1d4ed8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
    </style>
    """,
    unsafe_allow_html=True,
)

if not filtered:
    st.warning("⚠️ No items match your filters. Try clearing search or source filters.")
else:
    order = ["All News (24h)", "Interviews / DSA", "AI Trends", "Career", "For You"]
    tabs = st.tabs([f"{name} ({len(sections[name])})" for name in order])

    def render_card(it: dict, key_prefix: str):
        title = it.get("title") or "Untitled"
        url = it.get("url")
        dom = _domain_from_url(url or "")
        # Normalize bullets and strip any AI-intro prefixes
        bullets = [strip_ai_intro(b) for b in (it.get("bullets") or [])]
        if not bullets:
            # Fallback to summary sentence split if bullets missing
            summary_text = (it.get("summary", "") or "").replace("\r", " ").replace("\n", " ")
            if summary_text:
                bullets = [strip_ai_intro(s.strip().rstrip(" .")) for s in summary_text.split(". ") if s.strip()]
        # keep at most 4 non-empty bullets
        bullets = [b for b in bullets if b][:4]
        if not bullets:
            bullets = ["Summary not available. Click the link to read more."]
        # extra meta chips
        chips = []
        if it.get("company"):
            chips.append(f"<span class='badge'>🏢 {it['company']}</span>")
        if it.get("role"):
            chips.append(f"<span class='badge'>💼 {it['role']}</span>")
        if it.get("salary_hint"):
            chips.append(f"<span class='badge'>💰 {it['salary_hint']}</span>")
        
        # MSNRR Score badge
        msnrr_score = it.get("msnrr_score")
        if msnrr_score is not None:
            score_percent = int(msnrr_score * 100)
            score_color = "#10b981" if msnrr_score > 0.7 else "#f59e0b" if msnrr_score > 0.4 else "#ef4444"
            chips.append(f"<span class='badge' style='background: {score_color}'>⭐ MSNRR: {score_percent}%</span>")

        bullet_html = "".join([f"<li>{b}</li>" for b in bullets])
        link_html = f"<a href='{url}' target='_blank'>Read original</a>" if url else ""
        dom_html = f"<span class='badge'>{dom}</span>" if dom else ""
        # favicon logo (trial). Uses Google S2 favicons service
        logo_html = f"<img class='logo' src='https://www.google.com/s2/favicons?domain={dom}&sz=64' alt='logo'/>" if dom else ""
        tag_badges = " ".join([f"<span class='badge'>#{t}</span>" for t in (it.get("tags", []) or [])] + chips)
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

        # Bookmark actions area (always visible with appropriate message)
        act_col1, act_col2, act_col3, act_col4 = st.columns([0.15, 0.15, 0.15, 0.55])
        base_key = hashlib.md5((url or title or "").encode("utf-8", errors="ignore")).hexdigest()
        safe_key = f"{key_prefix}_{base_key}"
        if not st.session_state.token:
            with act_col1:
                st.button("Save", key=f"save_disabled_{safe_key}", disabled=True)
            with act_col2:
                st.caption("Login to save")
        elif not url:
            with act_col1:
                st.button("Save", key=f"save_nourl_{safe_key}", disabled=True)
            with act_col2:
                st.caption("No URL to bookmark")
        else:
            is_saved = url in saved_url_to_id
            with act_col1:
                if not is_saved and st.button("Save", key=f"save_{safe_key}"):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/user/bookmarks",
                            json={"title": title, "url": url},
                            headers={"Authorization": f"Bearer {st.session_state.token}"},
                            timeout=10,
                        )
                        if resp.status_code in (200, 201):
                            st.success("Saved")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
            with act_col2:
                if is_saved and st.button("Remove", key=f"remove_{safe_key}"):
                    try:
                        bid = saved_url_to_id.get(url)
                        if bid:
                            resp = requests.delete(
                                f"{API_BASE}/user/bookmarks/{bid}",
                                headers={"Authorization": f"Bearer {st.session_state.token}"},
                                timeout=10,
                            )
                            if resp.status_code == 200:
                                st.success("Removed")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Failed to remove: {e}")
            
            # Track click button
            with act_col3:
                if url and st.session_state.token:
                    if st.button("📊 Track", key=f"track_{safe_key}", help="Track this article for learning recommendations"):
                        try:
                            resp = requests.post(
                                f"{API_BASE}/api/tutor/track-click",
                                params={"article_url": url, "article_title": title},
                                headers={"Authorization": f"Bearer {st.session_state.token}"},
                                timeout=10,
                            )
                            if resp.status_code in (200, 201):
                                st.success("Tracked!")
                        except Exception as e:
                            st.error(f"Failed to track: {e}")

    for tab, name in zip(tabs, order):
        with tab:
            st.markdown(f"<div class='section-header'>{name}</div>", unsafe_allow_html=True)
            bucket = sections[name]
            # Vertical stacked feed
            for idx, it in enumerate(bucket):
                render_card(it, key_prefix=f"{name}_{idx}")

