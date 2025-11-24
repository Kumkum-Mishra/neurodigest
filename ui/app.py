import streamlit as st
import requests
import datetime


st.set_page_config(page_title="Login/Signup - AI Smart News Digest", layout="wide")

# Sidebar theme (app-wide)
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #0f172a 0%, #111827 60%, #1f2937 100%);
      border-right: 1px solid rgba(255,255,255,0.08);
    }
    [data-testid="stSidebar"] * { color: #e5e7eb !important; }
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 { color: #ffffff !important; }
    [data-testid="stSidebar"] .stButton>button {
      background: linear-gradient(135deg, #3b82f6, #1d4ed8);
      color: #ffffff; border: 0; border-radius: 10px; padding: 6px 10px;
      box-shadow: 0 2px 10px rgba(59,130,246,0.35);
    }
    [data-testid="stSidebar"] .stButton>button:hover { filter: brightness(1.05); }
    [data-testid="stSidebar"] .stTextInput>div>div>input,
    [data-testid="stSidebar"] .stTextArea>div>div>textarea,
    [data-testid="stSidebar"] .stSelectbox>div>div>div>div { 
      background: #0b1220; border: 1px solid rgba(148,163,184,0.25); border-radius: 10px; color: #e5e7eb;
    }
    [data-testid="stSidebar"] .stMultiSelect>div>div>div { 
      background: #0b1220; border: 1px solid rgba(148,163,184,0.25); border-radius: 10px; color: #e5e7eb;
    }
    [data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] { 
      background: #1f2937; border: 1px solid rgba(148,163,184,0.35);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Landing page: if logged-in, offer Dashboard; else show Login/Signup actions
st.markdown("""
<div style="text-align:center; padding:28px 0">
  <h1 style="margin-bottom:6px;">AI Smart News Digest</h1>
  <p style="color:#6b7280">Your personalized feed for Interviews, DSA, AI Trends and Career News</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.markdown("""
    <div style="border:2px solid #3b82f6; border-radius:20px; padding:32px; box-shadow:0 8px 32px rgba(59,130,246,0.3); background:linear-gradient(135deg,#1e40af,#3b82f6,#60a5fa)">
      <h3 style="text-align:center; margin:0 0 20px 0; color:#ffffff; font-size:3.2rem; font-weight:900; text-shadow:2px 2px 4px rgba(0,0,0,0.3)">Get Started</h3>
      <p style="text-align:center; color:#e0f2fe; font-size:1.1rem; margin:0">Join thousands of students preparing for placements</p>
    </div>
    """, unsafe_allow_html=True)

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

API_BASE = "http://localhost:8000"


# Lightweight session_state GET cache for the landing page to avoid
# triggering a full digest fetch immediately after login. Other pages
# (e.g. Dashboard) have their own caching too.
def _cached_get_simple(url: str, headers: dict | None, state_key: str, ttl: int = 60, force: bool = False):
    import time
    now = int(time.time())
    ts_key = f"{state_key}_ts"
    if not force and st.session_state.get(state_key) is not None and st.session_state.get(ts_key) is not None:
        if now - int(st.session_state.get(ts_key, 0)) < ttl:
            return st.session_state.get(state_key)

    try:
        if headers:
            resp = requests.get(url, headers=headers, timeout=12)
        else:
            resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            return None
        data = resp.json()
        st.session_state[state_key] = data
        st.session_state[ts_key] = now
        return data
    except Exception:
        return st.session_state.get(state_key)


# Cross-version safe rerun helper: some Streamlit versions use
# `experimental_rerun`, others provide `rerun`. Fall back to a
# session-state toggle if neither is available.
def _safe_rerun():
    try:
        return st.experimental_rerun()
    except Exception:
        try:
            return st.rerun()
        except Exception:
            st.session_state._reload = not st.session_state.get("_reload", False)
            return None

# If not logged in, show Login/Signup tabs right here
if not st.session_state.token:
    tabs = st.tabs(["Login", "Sign up"])
    with tabs[0]:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                try:
                    resp = requests.post(f"{API_BASE}/auth/login", data={"username": email, "password": password})
                    if resp.status_code == 200:
                        token = resp.json()["access_token"]
                        st.session_state.token = token
                        me = requests.get(f"{API_BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
                        if me.status_code == 200:
                            st.session_state.user = me.json()
                            st.success("Login successful. Loading dashboard…")
                            st.rerun()
                        else:
                            st.error("Failed to fetch user info")
                    else:
                        st.error("Invalid credentials")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    with tabs[1]:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            name = st.text_input("Full Name", key="signup_name")
            password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Sign up")
            if submitted:
                try:
                    resp = requests.post(
                        f"{API_BASE}/auth/signup",
                        json={"email": email, "password": password, "full_name": name},
                    )
                    if resp.status_code == 200:
                        st.success("Signup successful. Please log in.")
                    else:
                        st.error(resp.json().get("detail", "Signup failed"))
                except Exception as e:
                    st.error(f"Error: {str(e)}")
else:
    # Logged in: ensure we have user details and show dashboard feed inline
    # If we have a token but no user info, try to fetch it from the API.
    if st.session_state.token and not st.session_state.user:
        try:
            me = requests.get(
                f"{API_BASE}/auth/me",
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=10,
            )
            if me.status_code == 200:
                st.session_state.user = me.json()
            else:
                # Token invalid or expired: clear session and ask user to login again
                st.warning("Session invalid or expired — please log in again.")
                st.session_state.token = None
                st.session_state.user = None
                st.rerun()
        except Exception as e:
            # Non-fatal: leave user as None and show message
            st.error(f"Error fetching user info: {str(e)}")

    # Defensive access: user may still be None or not a dict
    user_obj = st.session_state.get("user") or {}
    email = None
    if isinstance(user_obj, dict):
        email = user_obj.get("email")
    else:
        # In case user is a Pydantic/SQLModel object
        email = getattr(user_obj, "email", None)

    if email:
        st.success(f"Logged in as {email}")
    else:
        st.success("Logged in")

    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()

    # Do not fetch the full digest on the landing/login page — that can be
    # expensive and causes duplicate fetches when users immediately
    # navigate. Offer a clear CTA to go to the Dashboard where digest is
    # loaded and cached.
    st.info("Your personalized digest is available on the Dashboard page.")
    if st.button("Open Dashboard"):
        # In Streamlit, redirecting to another page is done by instructing
        # the user to click the page sidebar; as a convenience we set a flag
        # so the Dashboard can check and immediately show cached data.
        st.session_state._open_dashboard = True
        _safe_rerun()

