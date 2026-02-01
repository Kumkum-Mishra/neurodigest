from fastapi import FastAPI, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from services.digest_service import run_full_pipeline, load_latest_digest, load_personalized_digest
from mcp_server.auth.routes_auth import router as auth_router
from mcp_server.preferences.routes_prefs import router as prefs_router
from mcp_server.user.routes_user import router as user_router
from mcp_server.tutor.routes_tutor import router as tutor_router
from storage.db import init_db
from mcp_server.auth.auth_utils import get_current_user
from storage.models import User
import time

app = FastAPI(title="AI Digest API", version="1.0.0")

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(prefs_router, prefix="/prefs", tags=["Preferences"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(tutor_router, prefix="/api", tags=["Tutor"])

# Initialize DB at module level (lazy, with error handling)
# This works for serverless because it only runs when module is imported
try:
    init_db()
    print("Database initialization attempted")
except Exception as e:
    print(f"Database initialization warning (will retry on first use): {e}")
    # Don't fail - will be initialized when first database operation happens

# Note: Scheduler removed for serverless compatibility
# Use Vercel Cron Jobs or external scheduler for scheduled tasks

# Root endpoint removed - frontend is served by Vercel static files
# If someone hits /api/root, they can get API info
@app.get("/api/root", tags=["Root"])
def api_root():
    """API root endpoint - returns API info."""
    return {
        "message": "NeuroDigest API",
        "version": "1.0.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "endpoints": {
            "digest": "/api/digest",
            "auth": "/auth/login",
            "user": "/user/bookmarks"
        }
    }

@app.get("/health", tags=["Health"])
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "NeuroDigest API"}

@app.get("/api/digest", tags=["Digest"])
def get_digest(background_tasks: BackgroundTasks, refresh: bool = False):
    """Return the latest saved digest. If the saved digest is older than
    DIGEST_FRESHNESS_SECONDS (env, default 3600s) schedule a background
    refresh so users get a fresher digest on subsequent requests.
    """
    payload = load_latest_digest()
    gen = payload.get("generated_at")
    try:
        freshness = int(os.getenv("DIGEST_FRESHNESS_SECONDS", "3600"))
    except Exception:
        freshness = 3600

    if refresh:
        print("/api/digest?refresh=1 called — running full pipeline synchronously")
        return run_full_pipeline()

    if not gen or (time.time() - gen) > freshness:
        background_tasks.add_task(run_full_pipeline)
    return payload


@app.get("/api/digest/me", tags=["Digest"])
def get_digest_for_user(current_user: User = Depends(get_current_user)):
    payload = load_personalized_digest(current_user.id)
    return {
        "user": {"id": current_user.id, "email": current_user.email},
        "digest": payload,
    }


@app.post("/api/trigger", tags=["Digest"])
def trigger_digest(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_full_pipeline)
    return {"status": "started"}


if __name__ == "__main__":
    uvicorn.run("mcp_server.main:app", host="0.0.0.0", port=8000, reload=True)
