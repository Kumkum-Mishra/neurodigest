import streamlit as st
from typing import Optional


def inject_css(path: Optional[str] = None):
    """Inject custom CSS from assets into the Streamlit page."""
    try:
        if not path:
            path = "ui/assets/style.css"
        with open(path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception:
        # best-effort; if file missing just skip
        pass


def render_card(title: str, subtitle: str = "", body: Optional[str] = None):
    html = '<div class="nd-card">'
    html += f'<div class="nd-header"><div class="nd-title">{title}</div>'
    if subtitle:
        html += f'<div class="nd-sub">{subtitle}</div>'
    html += '</div>'
    if body:
        html += f'<div>{body}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_article_card(title: str, url: str, meta: str = ""):
    html = '<div class="article-card">'
    html += f'<div class="article-title">{title}</div>'
    if meta:
        html += f'<div class="article-meta">{meta}</div>'
    html += f'<div style="margin-top:6px"><a href="{url}" target="_blank">Open</a></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def hero_banner(title: str, subtitle: str = "", cta: str | None = None):
    """Render a large hero/CTA block."""
    cta_html = f'<a class="cta" href="#">{cta}</a>' if cta else ""
    html = f'<div class="nd-hero glow"><div><div class="title">{title}</div><div class="subtitle">{subtitle}</div></div><div>{cta_html}</div></div>'
    st.markdown(html, unsafe_allow_html=True)


def render_metric(label: str, value: str | int | float, delta: str | None = None):
    """Render a compact KPI/metric box."""
    delta_html = f'<div class="delta">{delta}</div>' if delta else ''
    html = f'<div class="nd-metric"><div><div class="val">{value}</div><div class="lbl">{label}</div></div><div>{delta_html}</div></div>'
    st.markdown(html, unsafe_allow_html=True)
