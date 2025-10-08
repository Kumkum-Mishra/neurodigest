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
    # Logged in: show dashboard feed inline
    st.success(f"Logged in as {st.session_state.user.get('email')}")
    if st.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.rerun()

    with st.spinner("Fetching digest…"):
        data = _fetch_digest(st.session_state.token)

    gen = data.get("generated_at")
    if gen:
        st.caption("Last generated: " + datetime.datetime.fromtimestamp(gen).strftime("%Y-%m-%d %H:%M:%S"))

    items = data.get("items", [])
    if not items:
        st.warning("No items yet. Click Refresh in the dashboard page or try later.")
    else:
        for idx, it in enumerate(items):
            st.subheader(it.get("title", f"Untitled {idx+1}"))
            url = it.get("url")
            if url:
                st.markdown(f"[Read original]({url})")
            bullets = it.get("bullets", [])
            for b in bullets[:4]:
                st.markdown(f"- {b}")
            st.markdown("---")

