# storage/db.py
import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
from contextlib import contextmanager
from urllib.parse import urlparse, quote_plus

load_dotenv()

# Get DATABASE_URL with validation
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neurodigest.db")

# Validate and normalize DATABASE_URL
def normalize_database_url(url: str) -> str:
    """Normalize and validate database URL."""
    if not url or not url.strip():
        raise ValueError("DATABASE_URL is empty or not set")
    
    url = url.strip()
    
    # Handle postgresql:// URLs
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        # Parse the URL to validate it
        try:
            parsed = urlparse(url)
            if not parsed.hostname:
                raise ValueError("Invalid database URL: missing hostname")
            
            # Reconstruct URL with proper encoding
            # Handle password encoding (special characters)
            if parsed.password:
                # URL encode password if it contains special characters
                encoded_password = quote_plus(parsed.password)
                # Reconstruct URL with encoded password
                if "@" in url:
                    # Replace password part
                    parts = url.split("@")
                    if len(parts) == 2:
                        auth_part = parts[0]
                        if ":" in auth_part:
                            user_part = auth_part.split(":")[0]
                            url = f"{parsed.scheme}://{user_part}:{encoded_password}@{parsed.netloc.split('@')[-1]}{parsed.path}"
                            if parsed.query:
                                url += f"?{parsed.query}"
            
            # Ensure sslmode is set for Postgres
            if "sslmode" not in url and "?" not in url:
                url = f"{url}?sslmode=require"
            elif "sslmode" not in url and "?" in url:
                url = f"{url}&sslmode=require"
                
        except Exception as e:
            raise ValueError(f"Invalid database URL format: {e}")
    
    return url

# Normalize DATABASE_URL
try:
    DATABASE_URL = normalize_database_url(DATABASE_URL)
except Exception as e:
    print(f"Warning: Database URL normalization failed: {e}")
    print(f"Using DATABASE_URL as-is (may cause errors)")
    # Continue with original URL - might work if it's already correct

# Connection arguments setup
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("postgres"):
    connect_args = {}
else:
    connect_args = {}

# Create engine lazily - don't fail at module import time
# This allows the app to start even if DATABASE_URL is invalid
engine = None
_db_url_error = None

def get_engine():
    """Lazy engine creation with better error handling."""
    global engine, _db_url_error
    
    if engine is not None:
        return engine
    
    if _db_url_error is not None:
        raise _db_url_error
    
    try:
        # Try to create engine
        engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
        print("Database engine created successfully")
        return engine
    except Exception as e:
        error_msg = f"Could not create database engine: {e}"
        print(f"Database engine error: {error_msg}")
        # Don't print full URL for security, just first few chars
        url_preview = DATABASE_URL[:20] + "..." if len(DATABASE_URL) > 20 else DATABASE_URL
        print(f"DATABASE_URL preview: {url_preview}")
        _db_url_error = ValueError(error_msg)
        raise _db_url_error

# Don't create engine at module level - wait for first use
# This prevents import-time failures


def init_db():
    """Initialize database tables. Handles errors gracefully for serverless."""
    try:
        db_engine = get_engine()  # Get engine (lazy creation)
        import storage.models  # noqa: F401
        SQLModel.metadata.create_all(db_engine)
        print("Database tables created/verified")
    except Exception as e:
        print(f"Database initialization warning: {e}")
        # Don't raise - allow app to continue (tables might already exist)
        pass


# FastAPI dependency (use as Depends(get_session) in routes)
# Track if DB is initialized
_db_initialized = False

def get_session():
    """
    Use as a FastAPI dependency: `session: Session = Depends(get_session)`
    This generator yields a session and FastAPI ensures cleanup.
    Also ensures DB is initialized on first use.
    """
    global _db_initialized
    
    # Get engine (lazy creation if needed)
    db_engine = get_engine()
    
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f"DB init in get_session: {e}")
            # Continue anyway - might work if tables already exist
    
    session = Session(db_engine)
    try:
        yield session
    finally:
        session.close()
