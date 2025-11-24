# mcp_server/tutor/routes_tutor.py
"""
API routes for NDLRM (NeuroDigest Learning Recommendation Module)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional
import time

from storage.db import get_session
from storage.models import User, ArticleClick
from storage.models import LearningRoadmap
from mcp_server.auth.auth_utils import get_current_user
from services.ndlrm_service import (
    generate_learning_roadmap,
    get_user_roadmap,
    get_user_knowledge_profile,
    update_user_knowledge_profile,
    generate_tutor_response,
)

router = APIRouter(prefix="/tutor", tags=["Tutor"])


class RoadmapRequest(BaseModel):
    target_career: Optional[str] = None


class TutorQuestionRequest(BaseModel):
    question: str
    context: Optional[str] = None


@router.post("/roadmap")
def create_roadmap(
    request: RoadmapRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Generate a personalized weekly learning roadmap for the user.
    """
    try:
        result = generate_learning_roadmap(
            user_id=current_user.id,
            target_career=request.target_career
        )

        # result is expected to be {"roadmap": {...}, "topic_scores": {...}}
        roadmap = result.get("roadmap") if isinstance(result, dict) else result
        topic_scores = result.get("topic_scores") if isinstance(result, dict) else {}

        # Confirm persistence by retrieving the latest roadmap row for this user/week
        row = session.exec(
            select(LearningRoadmap)
            .where(
                LearningRoadmap.user_id == current_user.id,
            )
            .order_by(LearningRoadmap.generated_at.desc())
        ).first()

        resp = {
            "status": "success",
            "roadmap": roadmap,
            "user_id": current_user.id,
            "knowledge_profile": topic_scores,
        }
        if row:
            resp.update({"roadmap_id": row.id, "week_start": row.week_start})
        return resp
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate roadmap: {str(e)}")


@router.get("/roadmap")
def get_roadmap(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get the current week's learning roadmap for the user.
    """
    print(f"GET /api/tutor/roadmap called for user {current_user.id}")
    roadmap = get_user_roadmap(current_user.id)
    if not roadmap:
        print(f"No roadmap found for user {current_user.id}")
        return {
            "status": "not_found",
            "message": "No roadmap found. Generate one using POST /tutor/roadmap"
        }
    return {
        "status": "success",
        "roadmap": roadmap
    }


@router.get("/knowledge-profile")
def get_knowledge_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Get user's knowledge profile (topic scores).
    """
    # First try to read the persisted profile
    ukp = get_user_knowledge_profile(current_user.id)

    # If empty, compute/update it from bookmarks and clicks and return the result.
    # This makes the UI 'Refresh profile' button (which issues a GET) work
    # without requiring a separate POST endpoint.
    if not ukp:
        try:
            ukp = update_user_knowledge_profile(current_user.id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to compute knowledge profile: {e}")

    return {
        "status": "success",
        "knowledge_profile": ukp
    }


@router.post("/ask")
def ask_tutor(
    request: TutorQuestionRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Ask the AI tutor a question and get an educational response.
    """
    try:
        response = generate_tutor_response(
            user_id=current_user.id,
            question=request.question,
            context=request.context
        )
        # response may be a dict (structured feedback) or a string; return as-is
        return {
            "status": "success",
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")


@router.post("/track-click")
def track_article_click(
    article_url: str,
    article_title: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Track when a user clicks on an article (for engagement history scoring).
    """
    try:
        # Check if already tracked
        existing = session.exec(
            select(ArticleClick).where(
                ArticleClick.user_id == current_user.id,
                ArticleClick.article_url == article_url
            )
        ).first()
        
        if existing:
            return {"status": "already_tracked", "id": existing.id}
        
        click = ArticleClick(
            user_id=current_user.id,
            article_url=article_url,
            article_title=article_title or "",
            clicked_at=int(time.time())
        )
        session.add(click)
        session.commit()
        session.refresh(click)
        
        return {"status": "tracked", "id": click.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track click: {str(e)}")

