# storage/db.py
import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neurodigest.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db():
    import storage.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


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
