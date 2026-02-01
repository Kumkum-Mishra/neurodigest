import streamlit as st
import requests
import json
import time


st.set_page_config(page_title="AI Tutor • NeuroDigest — Personalized Content Digest & Learning Assistant", layout="wide")

# Robust import pattern so Tutor page works when run directly or as package
import os
import sys
try:
    from ui.ui_helpers import inject_css, render_card
except Exception:
    pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if pkg_root not in sys.path:
        sys.path.insert(0, pkg_root)
    from ui.ui_helpers import inject_css, render_card
inject_css()

# Cross-version safe rerun helper: some Streamlit versions use
# `experimental_rerun`, others provide `rerun`. Fall back to a
# session-state toggle if neither is available.
def _safe_rerun():
    try:
        # preferred in some versions
        return st.experimental_rerun()
    except Exception:
        try:
            return st.rerun()
        except Exception:
            # best-effort fallback: flip a session flag so UI updates
            st.session_state._reload = not st.session_state.get("_reload", False)
            return None

API_BASE = "http://localhost:8000"


# Simple client-side GET cache to avoid refetching on every Streamlit rerun.
# Stores responses in `st.session_state` with a timestamp. Call with
# `cached_get(f"{API_BASE}/api/tutor/roadmap", headers, 'latest_roadmap', ttl=120)`.
def cached_get(url: str, headers: dict, state_key: str, ttl: int = 120, force: bool = False):
    now = int(time.time())
    ts_key = f"{state_key}_ts"

    if not force and st.session_state.get(state_key) is not None and st.session_state.get(ts_key) is not None:
        age = now - int(st.session_state.get(ts_key, 0))
        if age < ttl:
            return st.session_state.get(state_key)

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # store raw useful payload depending on endpoint shape
            # if the endpoint returns {'status':'success','roadmap':...}
            if isinstance(data, dict) and data.get('status') == 'success':
                # try to store the main payload automatically
                if 'roadmap' in data:
                    value = data.get('roadmap')
                elif 'knowledge_profile' in data:
                    value = data.get('knowledge_profile')
                else:
                    value = data
            else:
                value = data

            st.session_state[state_key] = value
            st.session_state[ts_key] = now
            return value
        else:
            # Return cached value if available even on error
            return st.session_state.get(state_key)
    except Exception:
        # network error/timeouts: fall back to cached value if any
        return st.session_state.get(state_key)


def _normalize_roadmaps(obj):
    """Return a list of roadmap dicts from various possible API shapes."""
    if not obj:
        return []
    # if it's a JSON string, try to parse
    if isinstance(obj, str):
        try:
            parsed = json.loads(obj)
        except Exception:
            return []
        return _normalize_roadmaps(parsed)

    if isinstance(obj, dict):
        # API may return {'status':'success','roadmap': [...]}
        if 'roadmap' in obj and isinstance(obj['roadmap'], list):
            return obj['roadmap']
        # Or single roadmap dict
        return [obj]

    if isinstance(obj, list):
        out = []
        for it in obj:
            if isinstance(it, str):
                try:
                    out.append(json.loads(it))
                except Exception:
                    continue
            else:
                out.append(it)
        return out

    return []

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

st.title("🤖 AI Tutor - NDLRM")
st.markdown("**Personalized Learning Recommendation Module**")

render_card("AI Tutor", "Generate learning roadmaps & practice questions", "Generate role-based roadmaps, view your knowledge profile, and get AI feedback on answers. Click a section from the sidebar to begin.")

if not st.session_state.token:
    st.warning("Please log in to access the AI Tutor.")
    st.stop()

# Sidebar for navigation
st.sidebar.title("NDLRM Features")
page = st.sidebar.radio(
    "Choose a feature:",
    ["Learning Roadmap", "Knowledge Profile", "Ask Tutor", "Practice Questions"]
)

headers = {"Authorization": f"Bearer {st.session_state.token}"}

if page == "Learning Roadmap":
    st.header("📚 Your Weekly Learning Roadmap")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        target_career = st.text_input("Target Career", value="AI Engineer", key="career_input")
        if st.button("Generate Roadmap", type="primary"):
            with st.spinner("Generating your personalized roadmap..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/api/tutor/roadmap",
                        json={"target_career": target_career},
                        headers=headers,
                        timeout=60
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        rid = data.get("roadmap_id")
                        kp = data.get("knowledge_profile")
                        if rid:
                            st.success(f"Roadmap generated! (id={rid})")
                        else:
                            st.success("Roadmap generated!")
                        # Refresh cached list of roadmaps so UI shows all role variants
                        latest = cached_get(f"{API_BASE}/api/tutor/roadmap", headers, "latest_roadmaps", ttl=60, force=True)
                        if latest is not None:
                            st.session_state.latest_roadmaps = latest
                        if kp is not None:
                            st.session_state.latest_ukp = kp
                        # Render immediately
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to generate roadmap: {e}")
    
    roadmaps = st.session_state.get("latest_roadmaps") or cached_get(f"{API_BASE}/api/tutor/roadmap", headers, "latest_roadmaps", ttl=300)
    roadmaps = _normalize_roadmaps(roadmaps)

    if roadmaps:
        # roadmaps is expected to be a list of {id, target_career, generated_at, week_start, roadmap}
        for idx, r in enumerate(roadmaps, 1):
            if not isinstance(r, dict):
                continue
            role = r.get("target_career") or r.get("roadmap", {}).get("target_career") or "(unspecified)"
            gen = r.get("generated_at") or r.get("created_at")
            if isinstance(gen, (int, float)):
                gen_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(gen))
            else:
                gen_str = str(gen) if gen else 'unknown'
            with st.expander(f"{idx}. Role: {role} — generated: {gen_str}", expanded=(idx==1)):
                roadmap_body = r.get("roadmap") or r
                # Week Plan
                st.subheader("Week Plan")
                week_plan = roadmap_body.get("week_plan", []) if isinstance(roadmap_body, dict) else []
                for i, topic_item in enumerate(week_plan, 1):
                    with st.expander(f"Topic {i}: {topic_item.get('topic', 'N/A')}"):
                        resources = topic_item.get("resources", [])
                        for j, resource in enumerate(resources, 1):
                            st.markdown(f"{j}. {resource}")

                # Skills to Learn
                st.subheader("Skills to Learn")
                skills = roadmap_body.get("skills_to_learn", []) if isinstance(roadmap_body, dict) else []
                for skill in skills:
                    st.markdown(f"- {skill}")

                # Practice Questions
                st.subheader("Practice Questions")
                questions = roadmap_body.get("practice_questions", []) if isinstance(roadmap_body, dict) else []
                for i, q in enumerate(questions, 1):
                    st.markdown(f"**{i}.** {q}")

                # Recommended Projects
                st.subheader("Recommended Projects")
                projects = roadmap_body.get("recommended_projects", []) if isinstance(roadmap_body, dict) else []
                for i, project in enumerate(projects, 1):
                    st.markdown(f"{i}. {project}")
    else:
        st.info("No roadmap found. Click 'Generate Roadmap' to create one.")

elif page == "Knowledge Profile":
    st.header("Your Knowledge Profile")
    st.markdown("Based on your article engagement and interests")
    # Prefer recently-generated profile stored in session state
    profile = st.session_state.get("latest_ukp")

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Refresh profile"):
            with st.spinner("Refreshing knowledge profile..."):
                # Force a fresh fetch and update the session cache
                with st.spinner("Refreshing knowledge profile..."):
                    profile = cached_get(f"{API_BASE}/api/tutor/knowledge-profile", headers, "latest_ukp", ttl=60, force=True)
                    if profile is not None:
                        st.session_state.latest_ukp = profile
                        try:
                            _safe_rerun()
                        except Exception:
                            pass
                    else:
                        st.error("Failed to refresh profile. Check your connection or try again.")

    # If not present in session state, attempt a one-time fetch
    if profile is None:
        profile = cached_get(f"{API_BASE}/api/tutor/knowledge-profile", headers, "latest_ukp", ttl=300)
        if profile is None:
            profile = {}

    if profile:
        st.subheader("Topic Scores")
        # Sort by score
        sorted_topics = sorted(profile.items(), key=lambda x: x[1], reverse=True)
        for topic, score in sorted_topics:
            # show topic label and percent + a progress bar
            st.markdown(f"**{topic}** — {score:.0%}")
            st.progress(score)
    else:
        st.info("No knowledge profile yet. Start bookmarking articles to build your profile!")
        st.markdown("If you already have bookmarks or article clicks, click **Refresh profile** to compute your topic scores.")
        # Show example placeholder so it's clear what will appear
        st.subheader("Example topics (when available)")
        example = {"machine learning": 0.85, "python": 0.6, "nlp": 0.45}
        for topic, score in example.items():
            st.markdown(f"**{topic}** — {score:.0%}")
            st.progress(score)

elif page == "Ask Tutor":
    st.header("Ask the AI Tutor")
    st.markdown("Get personalized explanations and learning guidance")
    
    question = st.text_area("Your Question", height=100, placeholder="e.g., What is reinforcement learning?")
    context = st.text_area("Additional Context (optional)", height=50, placeholder="e.g., I'm reading about RL in my AI course")
    
    if st.button("Ask Tutor", type="primary"):
        if question:
            with st.spinner("Thinking..."):
                try:
                    resp = requests.post(
                        f"{API_BASE}/api/tutor/ask",
                        json={"question": question, "context": context if context else None},
                        headers=headers,
                        timeout=30
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        response = data.get("response", "")
                        st.markdown("### Tutor's Response:")
                        st.markdown(response)
                    else:
                        st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Failed to get response: {e}")
        else:
            st.warning("Please enter a question.")

elif page == "Practice Questions":
    st.header("Practice Questions")
    st.markdown("Interview-style questions based on your learning roadmap")

    # fetch all roadmaps and collect practice questions grouped by role
    all_roadmaps = st.session_state.get("latest_roadmaps") or cached_get(f"{API_BASE}/api/tutor/roadmap", headers, "latest_roadmaps", ttl=300)
    all_roadmaps = _normalize_roadmaps(all_roadmaps)

    if not all_roadmaps:
        st.info("No roadmaps found. Generate one first.")
    else:
        role_groups = {}
        for r in all_roadmaps:
            if not isinstance(r, dict):
                continue
            role = r.get("target_career") or r.get("roadmap", {}).get("target_career") or "(unspecified)"
            roadmap_obj = r.get("roadmap") if isinstance(r.get("roadmap"), dict) else r
            questions = roadmap_obj.get("practice_questions", []) if isinstance(roadmap_obj, dict) else []
            role_groups.setdefault(role, []).extend(questions)

        for role, questions in role_groups.items():
            with st.expander(f"Practice Questions — {role} ({len(questions)})"):
                if not questions:
                    st.info("No practice questions for this roadmap.")
                    continue
                for qi, q in enumerate(questions, 1):
                    with st.expander(f"Question {qi}"):
                        st.markdown(f"**{q}**")
                        answer_key = f"pq_{role}_{qi}_answer"
                        fb_key = f"pq_{role}_{qi}_feedback"
                        get_fb_key = f"pq_get_feedback_{role}_{qi}"
                        answer = st.text_area("Your Answer", key=answer_key, height=100)
                        col1, col2 = st.columns([0.3, 0.7])
                        with col1:
                            if st.button("Get Feedback", key=get_fb_key):
                                if not answer or not answer.strip():
                                    st.warning("Please write an answer before requesting feedback.")
                                else:
                                    try:
                                        resp = requests.post(
                                            f"{API_BASE}/api/tutor/ask",
                                            json={"question": q, "context": answer},
                                            headers=headers,
                                            timeout=120,
                                        )
                                        if resp.status_code == 200:
                                            data = resp.json()
                                            feedback = data.get("response", "No feedback returned.")
                                            st.session_state[fb_key] = feedback
                                            try:
                                                _safe_rerun()
                                            except Exception:
                                                pass
                                            st.success("Feedback received")
                                        else:
                                            st.error(f"Error getting feedback: {resp.text}")
                                    except Exception as e:
                                        st.error(f"Failed to get feedback: {e}")
                        with col2:
                            existing_fb = st.session_state.get(fb_key)
                            if existing_fb:
                                st.markdown("### Feedback:")
                                if isinstance(existing_fb, dict):
                                    score = existing_fb.get("score")
                                    critique = existing_fb.get("critique")
                                    improvements = existing_fb.get("improvements")
                                    example = existing_fb.get("example_answer") or existing_fb.get("example")
                                    refs = existing_fb.get("references") or existing_fb.get("refs")
                                    if score is not None:
                                        st.markdown(f"**Score:** {score}/5")
                                    if critique:
                                        st.markdown(f"**Critique:** {critique}")
                                    if improvements:
                                        st.markdown("**Improvements:**")
                                        for itm in (improvements if isinstance(improvements, list) else [improvements]):
                                            st.markdown(f"- {itm}")
                                    if example:
                                        st.markdown("**Example answer:**")
                                        st.markdown(example)
                                    if refs:
                                        st.markdown("**References:**")
                                        for rr in (refs if isinstance(refs, list) else [refs]):
                                            st.markdown(f"- {rr}")
                                else:
                                    st.markdown(existing_fb)

