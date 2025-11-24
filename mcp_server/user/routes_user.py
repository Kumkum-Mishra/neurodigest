# mcp_server/user/routes_user.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from storage.db import get_session
from storage.models import UserPreference, User, Bookmark
from mcp_server.auth.auth_utils import get_current_user

router = APIRouter(tags=["User"])

class PrefPayload(BaseModel):
    keywords: str | None = ""   # comma-separated
    sources: str | None = ""    # comma-separated

@router.get("/prefs")
def get_prefs(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    q = select(UserPreference).where(UserPreference.user_id == current_user.id)
    prefs = session.exec(q).first()
    if not prefs:
        return {"keywords": "", "sources": ""}
    return {"keywords": prefs.keywords, "sources": prefs.sources}

@router.post("/prefs")
def set_prefs(payload: PrefPayload, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    q = select(UserPreference).where(UserPreference.user_id == current_user.id)
    prefs = session.exec(q).first()
    if not prefs:
        prefs = UserPreference(user_id=current_user.id, keywords=payload.keywords or "", sources=payload.sources or "")
        session.add(prefs)
    else:
        prefs.keywords = payload.keywords or ""
        prefs.sources = payload.sources or ""
    session.commit()
    session.refresh(prefs)
    return {"msg": "Preferences saved", "prefs": {"keywords": prefs.keywords, "sources": prefs.sources}}


# --- Bookmarks ---
class BookmarkPayload(BaseModel):
    title: str
    url: str


@router.get("/bookmarks")
def list_bookmarks(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    rows = session.exec(select(Bookmark).where(Bookmark.user_id == current_user.id)).all()
    return [{"id": b.id, "title": b.title, "url": b.url, "added_at": b.added_at} for b in rows]


@router.post("/bookmarks")
def save_bookmark(payload: BookmarkPayload, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    # dedupe by url per user
    existing = session.exec(select(Bookmark).where(Bookmark.user_id == current_user.id, Bookmark.url == payload.url)).first()
    if existing:
        return {"id": existing.id, "title": existing.title, "url": existing.url}
    b = Bookmark(user_id=current_user.id, title=payload.title, url=payload.url)
    session.add(b)
    session.commit()
    session.refresh(b)
    return {"id": b.id, "title": b.title, "url": b.url}


@router.delete("/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    b = session.get(Bookmark, bookmark_id)
    if not b or b.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    session.delete(b)
    session.commit()
    return {"status": "deleted"}
