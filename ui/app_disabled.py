"""
Disabled legacy entrypoint.

This file replaces the previous `ui/app.py` to avoid Streamlit showing
an 'app' label in the UI navigation. The real login page is `ui/login.py`.

If you need to restore, rename this file back to `app.py`.
"""

# Intentionally empty; use `streamlit run ui/login.py` instead.
