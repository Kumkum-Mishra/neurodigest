from fastapi import FastAPI, BackgroundTasks, Depends
from apscheduler.schedulers.background import BackgroundScheduler
import uvicorn

from services.digest_service import run_full_pipeline, load_latest_digest, load_personalized_digest
from mcp_server.auth.routes_auth import router as auth_router
from mcp_server.preferences.routes_prefs import router as prefs_router
from storage.db import init_db
from mcp_server.auth.auth_utils import get_current_user
from storage.models import User

# === Initialize FastAPI App ===
app = FastAPI(title="AI Digest API", version="1.0.0")

# ✅ Mount routers with proper prefixes
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(prefs_router, prefix="/prefs", tags=["Preferences"])

# Background scheduler for daily tasks
scheduler = BackgroundScheduler()


# === Lifecycle Events ===
@app.on_event("startup")
def on_startup():
    init_db()
    scheduler.add_job(run_full_pipeline, "cron", hour=9, minute=0)
    scheduler.start()
    print("✅ Scheduler started: daily run at 9:00 AM")


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)
    print("🛑 Scheduler stopped")


# === Digest Endpoints ===

# Public digest (accessible to anyone)
@app.get("/api/digest", tags=["Digest"])
def get_digest():
    return load_latest_digest()


# Personalized digest (requires login)
@app.get("/api/digest/me", tags=["Digest"])
def get_digest_for_user(current_user: User = Depends(get_current_user)):
    payload = load_personalized_digest(current_user.id)
    return {
        "user": {"id": current_user.id, "email": current_user.email},
        "digest": payload,
    }


# Manual trigger (admin-style endpoint)
@app.post("/api/trigger", tags=["Digest"])
def trigger_digest(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_full_pipeline)
    return {"status": "started"}


# === Entrypoint ===
if __name__ == "__main__":
    uvicorn.run("mcp_server.main:app", host="0.0.0.0", port=8000, reload=True)
