from sqlmodel import SQLModel, Field
from typing import Optional
import time


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: int = Field(default_factory=lambda: int(time.time()))


class UserPreference(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    keywords: Optional[str] = Field(default="")    # comma-separated keywords
    sources: Optional[str] = Field(default="")     # comma-separated sources
    match_mode: str = Field(default="or")          # "or" or "and"
    created_at: int = Field(default_factory=lambda: int(time.time()))


class Bookmark(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    title: str
    url: str
    added_at: int = Field(default_factory=lambda: int(time.time()))
