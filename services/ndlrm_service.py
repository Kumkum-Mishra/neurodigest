# services/ndlrm_service.py
"""
NDLRM: NeuroDigest Learning Recommendation Module

Generates personalized weekly learning roadmaps based on user's article engagement.
"""
import os
import json
import time
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlmodel import select, Session
from dotenv import load_dotenv

from storage.db import engine
from storage.models import UserKnowledgeProfile, LearningRoadmap, Bookmark, ArticleClick
from sqlalchemy import text

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL")


def extract_topics_from_articles(user_id: int) -> List[str]:
    """
    Extract topics from user's bookmarked and clicked articles.
    Returns list of topic keywords.
    """
    topics = set()
    
    try:
        with Session(engine) as session:
            # Get bookmarked articles
            bookmarks = session.exec(
                select(Bookmark).where(Bookmark.user_id == user_id)
            ).all()
            
            # Get clicked articles
            clicks = session.exec(
                select(ArticleClick).where(ArticleClick.user_id == user_id)
            ).all()
            
            # Extract topics from titles
            for bm in bookmarks:
                title_lower = (bm.title or "").lower()
                # Simple keyword extraction
                topic_keywords = [
                    "ai", "machine learning", "deep learning", "llm", "neural network",
                    "reinforcement learning", "nlp", "computer vision", "transformer",
                    "interview", "dsa", "system design", "algorithm", "data structure",
                    "python", "javascript", "react", "node", "backend", "frontend",
                    "docker", "kubernetes", "aws", "cloud", "devops",
                    "research", "paper", "arxiv", "tutorial", "guide"
                ]
                for keyword in topic_keywords:
                    if keyword in title_lower:
                        topics.add(keyword)
            
            for click in clicks:
                title_lower = (click.article_title or "").lower()
                for keyword in topic_keywords:
                    if keyword in title_lower:
                        topics.add(keyword)
    
    except Exception as e:
        print(f"Error extracting topics: {e}")
    
    return list(topics)


def update_user_knowledge_profile(user_id: int) -> Dict[str, float]:
    """
    Update User Knowledge Profile (UKP) based on engagement.
    Returns topic scores as dict: {"ai": 0.8, "ml": 0.5, ...}
    """
    topics = extract_topics_from_articles(user_id)
    
    # Count topic frequencies
    topic_counts: Dict[str, int] = {}
    for topic in topics:
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    # Normalize to [0, 1] scores
    max_count = max(topic_counts.values()) if topic_counts else 1
    topic_scores = {topic: min(1.0, count / max_count) for topic, count in topic_counts.items()}
    
    # Save to database
    try:
        with Session(engine) as session:
            ukp = session.exec(
                select(UserKnowledgeProfile).where(UserKnowledgeProfile.user_id == user_id)
            ).first()
            
            if ukp:
                ukp.topic_scores = json.dumps(topic_scores)
                ukp.last_updated = int(time.time())
            else:
                ukp = UserKnowledgeProfile(
                    user_id=user_id,
                    topic_scores=json.dumps(topic_scores),
                    last_updated=int(time.time())
                )
                session.add(ukp)
            
            session.commit()
            session.refresh(ukp)
    except Exception as e:
        print(f"Error updating UKP: {e}")
    
    return topic_scores


def estimate_difficulty(article_title: str, article_summary: str) -> str:
    """
    Estimate article difficulty: "beginner", "intermediate", "advanced"
    """
    text = (article_title + " " + article_summary).lower()
    
    beginner_keywords = ["tutorial", "introduction", "getting started", "basics", "beginner", "guide"]
    advanced_keywords = ["research", "paper", "arxiv", "implementation", "deep dive", "advanced", "optimization"]
    
    beginner_score = sum(1 for kw in beginner_keywords if kw in text)
    advanced_score = sum(1 for kw in advanced_keywords if kw in text)
    
    if advanced_score > beginner_score:
        return "advanced"
    elif beginner_score > 0:
        return "beginner"
    else:
        return "intermediate"


def generate_learning_roadmap(user_id: int, target_career: Optional[str] = None) -> Dict:
    """
    Generate personalized weekly learning roadmap using LLM.
    """
    # Update knowledge profile first
    topic_scores = update_user_knowledge_profile(user_id)
    
    # Get user's recent engagement
    topics = list(topic_scores.keys())[:10]  # Top 10 topics
    topics_str = ", ".join(topics) if topics else "general programming"
    
    # Prepare prompt for LLM
    prompt = f"""Generate a personalized weekly learning roadmap for a student interested in {target_career or "software engineering"}.

User's current interests (from article engagement): {topics_str}

Provide a structured weekly plan with:
1. Week Plan: List 3-5 topics to focus on this week, each with 2-3 learning resources (tutorials, papers, videos)
2. Skills to Learn: List 3-5 specific skills to develop
3. Practice Questions: 5-7 interview-style questions related to the topics
4. Recommended Projects: 2-3 project ideas to practice

Format as JSON with keys: week_plan, skills_to_learn, practice_questions, recommended_projects.

Example format:
{{
  "week_plan": [
    {{
      "topic": "Reinforcement Learning",
      "resources": [
        "RL tutorial on OpenAI blog",
        "Deep RL course on Coursera",
        "Paper: Proximal Policy Optimization"
      ]
    }}
  ],
  "skills_to_learn": ["Q-learning", "Policy gradients", "Value functions"],
  "practice_questions": [
    "Explain the difference between on-policy and off-policy RL",
    "Implement a simple Q-learning agent",
    "What is the exploration-exploitation tradeoff?"
  ],
  "recommended_projects": [
    "Build a cart-pole RL agent",
    "Implement a multi-armed bandit solver"
  ]
}}"""

    # Call LLM (Groq or Ollama)
    roadmap_data = None
    
    if GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are an expert learning advisor. Generate structured, actionable learning roadmaps in JSON format."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"].strip()
                # Try to extract JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                roadmap_data = json.loads(content)
        except Exception as e:
            print(f"Error calling Groq for roadmap: {e}")
    
    if not roadmap_data and OLLAMA_URL:
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "phi3", "prompt": prompt, "stream": False},
                timeout=60
            )
            content = response.json().get("response", "")
            # Try to parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            roadmap_data = json.loads(content)
        except Exception as e:
            print(f"Error calling Ollama for roadmap: {e}")
    
    # Fallback if LLM fails
    if not roadmap_data:
        roadmap_data = {
            "week_plan": [
                {
                    "topic": topics[0] if topics else "General Programming",
                    "resources": [
                        "Search for tutorials on the topic",
                        "Practice with coding exercises",
                        "Read documentation"
                    ]
                }
            ],
            "skills_to_learn": topics[:5] if topics else ["Programming fundamentals"],
            "practice_questions": [
                "What are the key concepts in this topic?",
                "How would you explain this to a beginner?",
                "What are common interview questions about this?"
            ],
            "recommended_projects": [
                "Build a small project using the concepts",
                "Implement a tutorial from scratch"
            ]
        }
    
    # Save roadmap to database
    week_start = int((datetime.now() - timedelta(days=datetime.now().weekday())).timestamp())
    
    try:
        # Ensure DB schema includes `target_career` column (safe ALTER for existing DBs)
        try:
            with engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info('learningroadmap')")).fetchall()
                cols = [r[1] for r in res]
                if 'target_career' not in cols:
                    conn.execute(text("ALTER TABLE learningroadmap ADD COLUMN target_career TEXT"))
                    conn.commit()
        except Exception as ex_schema:
            # Non-fatal: log and continue — insertion may still fail and will be handled below
            print(f"Warning: failed to ensure schema for learningroadmap: {ex_schema}")

        with Session(engine) as session:
            roadmap = LearningRoadmap(
                user_id=user_id,
                week_start=week_start,
                roadmap_data=json.dumps(roadmap_data),
                target_career=target_career,
                generated_at=int(time.time())
            )
            session.add(roadmap)
            session.commit()
            session.refresh(roadmap)
    except Exception as e:
        print(f"Error saving roadmap: {e}")
        # Propagate the exception so the API returns 500 and the UI doesn't show a false success.
        raise

    # Return the roadmap and the updated topic scores so callers (API/UI)
    # can render both immediately without needing a separate GET.
    return {"roadmap": roadmap_data, "topic_scores": topic_scores}


def get_user_roadmap(user_id: int) -> Optional[Dict]:
    """
    Get all learning roadmaps for a user ordered by generated_at desc.
    """
    try:
        with Session(engine) as session:
            rows = session.exec(
                select(LearningRoadmap)
                .where(LearningRoadmap.user_id == user_id)
                .order_by(LearningRoadmap.generated_at.desc())
            ).all()
            result = []
            for r in rows:
                try:
                    rd = json.loads(r.roadmap_data)
                except Exception:
                    rd = {}
                result.append({
                    "id": r.id,
                    "user_id": r.user_id,
                    "target_career": r.target_career,
                    "generated_at": r.generated_at,
                    "week_start": r.week_start,
                    "roadmap": rd,
                })
            return result
    except Exception as e:
        print(f"Error getting roadmap: {e}")
    return []


def get_user_knowledge_profile(user_id: int) -> Dict[str, float]:
    """
    Get user's knowledge profile topic scores.
    """
    try:
        with Session(engine) as session:
            ukp = session.exec(
                select(UserKnowledgeProfile).where(UserKnowledgeProfile.user_id == user_id)
            ).first()
            
            if ukp and ukp.topic_scores:
                return json.loads(ukp.topic_scores)
    except Exception as e:
        print(f"Error getting UKP: {e}")
    
    return {}


def generate_tutor_response(user_id: int, question: str, context: Optional[str] = None) -> str:
    """
    Generate AI tutor response to user's question.
    """
    ukp = get_user_knowledge_profile(user_id)
    topics_str = ", ".join(list(ukp.keys())[:5]) if ukp else "general programming"

    # Structured feedback prompt: request JSON with score, critique, suggestions, example_answer
    prompt = f"""
You are an expert AI tutor. Provide structured feedback for a student's answer.

Context topics: {topics_str}

Student's question: {question}

Student's answer / context: {context or ""}

Return a JSON object with these keys:
- score: integer 1-5 (1 poor, 5 excellent)
- critique: short paragraph (2-4 sentences) describing strengths and weaknesses
- improvements: list of 3 concise actional suggestions to improve the answer
- example_answer: a short high-quality example answer (1-3 sentences)
- references: optional list of 1-3 resources (URLs or titles)

Return only valid JSON (no surrounding explanation). If you cannot produce structured JSON, return a JSON object with a single key `text` containing a helpful reply.
"""

    def _call_groq(prompt_text: str, timeout: int = 60):
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI tutor. Provide clear, educational feedback."},
                    {"role": "user", "content": prompt_text},
                ],
                "temperature": 0.6,
            }
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Error calling Groq for tutor: {e}")
        return None

    def _call_ollama(prompt_text: str, timeout: int = 90):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "phi3", "prompt": prompt_text, "stream": False},
                timeout=timeout,
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            print(f"Error calling Ollama for tutor: {e}")
        return None

    content = None
    if GROQ_API_KEY:
        content = _call_groq(prompt, timeout=60)

    if not content and OLLAMA_URL:
        content = _call_ollama(prompt, timeout=90)

    if not content:
        # Fallback plain text
        fallback = (
            "I'm sorry, I couldn't generate structured feedback right now. "
            "Try again later or ask the tutor a simpler question."
        )
        return {"text": fallback}

    # Try to extract JSON from model output
    try:
        if "```json" in content:
            json_text = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_text = content.split("```")[1].split("```")[0].strip()
        else:
            json_text = content.strip()

        # If the model appended explanatory text, attempt to find the first '{'...
        if not json_text.strip().startswith("{"):
            idx = json_text.find("{")
            if idx != -1:
                json_text = json_text[idx:]

        result = json.loads(json_text)
        return result
    except Exception:
        # Return raw text wrapped in a dict for UI
        return {"text": content}

