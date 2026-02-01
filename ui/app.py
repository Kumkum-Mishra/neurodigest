"""
Compatibility stub: the login page was renamed to `login.py`.

This file keeps a small shim so if someone runs `streamlit run ui/app.py`
it will load the real `ui/login.py` and set a clearer page title.
"""

import streamlit as st
from importlib import import_module

# Ensure the page title shows 'Login' when this file is the entrypoint
st.set_page_config(page_title="Login/Signup - NeuroDigest — Personalized Content Digest & Learning Assistant", layout="wide")

# Import the renamed module so the same UI is shown
try:
    import_module("ui.login")
except Exception:
    # Fall back to a helpful message if the module import fails
    st.error("The login page module could not be loaded. Try running `streamlit run ui/login.py`.")

