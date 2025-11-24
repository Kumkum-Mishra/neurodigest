from fastapi import FastAPI, BackgroundTasks, Depends
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn

from services.digest_service import run_full_pipeline, load_latest_digest, load_personalized_digest
from mcp_server.auth.routes_auth import router as auth_router
from mcp_server.preferences.routes_prefs import router as prefs_router
from mcp_server.user.routes_user import router as user_router
from mcp_server.tutor.routes_tutor import router as tutor_router
from storage.db import init_db
from mcp_server.auth.auth_utils import get_current_user
from storage.models import User
import time
import os

app = FastAPI(title="AI Digest API", version="1.0.0")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(prefs_router, prefix="/prefs", tags=["Preferences"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(tutor_router, prefix="/api", tags=["Tutor"])

scheduler = BackgroundScheduler()

@app.on_event("startup")
def on_startup():
    init_db()
    scheduler.add_job(run_full_pipeline, "cron", hour=9, minute=0)
    scheduler.start()
    print("Scheduler started: daily run at 9:00 AM")


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)
    print("Scheduler stopped")

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
