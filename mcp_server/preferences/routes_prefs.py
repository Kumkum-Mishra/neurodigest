from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from storage.db import get_session
from storage.models import UserPreference, User
from mcp_server.auth.routes_auth import get_current_user

router = APIRouter(tags=["Preferences"])


@router.get("/me", response_model=UserPreference)
def get_my_preferences(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    prefs = session.exec(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    ).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not set")
    return prefs


@router.post("/me", response_model=UserPreference)
def set_my_preferences(
    keywords: str = "",
    sources: str = "",
    match_mode: str = "or",
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if match_mode not in ["or", "and"]:
        raise HTTPException(status_code=400, detail="match_mode must be 'or' or 'and'")

    prefs = session.exec(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    ).first()
    if prefs:
        prefs.keywords = keywords
        prefs.sources = sources
        prefs.match_mode = match_mode
    else:
        prefs = UserPreference(
            user_id=current_user.id,
            keywords=keywords,
            sources=sources,
            match_mode=match_mode,
        )
        session.add(prefs)

    session.commit()
    session.refresh(prefs)
    return prefs
