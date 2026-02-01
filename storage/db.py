# storage/db.py
import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neurodigest.db")

# Connection arguments setup
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql"):
    # For Neon/Postgres: ensure SSL is handled properly
    # If connection string doesn't have sslmode, add it
    if "sslmode" not in DATABASE_URL and "?" not in DATABASE_URL:
        DATABASE_URL = f"{DATABASE_URL}?sslmode=require"
    connect_args = {}
else:
    connect_args = {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db():
    """Initialize database tables. Handles errors gracefully for serverless."""
    try:
        import storage.models  # noqa: F401
        SQLModel.metadata.create_all(engine)
        print("Database tables created/verified")
    except Exception as e:
        print(f"Database initialization warning: {e}")
        # Don't raise - allow app to continue (tables might already exist)
        pass


# FastAPI dependency (use as Depends(get_session) in routes)
def get_session():
    """
    Use as a FastAPI dependency: `session: Session = Depends(get_session)`
    This generator yields a session and FastAPI ensures cleanup.
    """
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
