"""
Vercel serverless function wrapper for FastAPI app.
Vercel Python runtime automatically detects 'app' variable in this file.
"""
import sys
import os

# Add project root to path FIRST
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import FastAPI - this must succeed
from fastapi import FastAPI

# Initialize app variable - Vercel needs this at module level
# First, try to import the real app
app = None
import_error = None

try:
    from mcp_server.main import app
    # Success - app is imported
    print("Successfully imported FastAPI app")
except Exception as e:
    # Import failed - create fallback app with better error info
    import_error = str(e)
    import traceback
    error_trace = traceback.format_exc()
    
    print(f"Failed to import app: {import_error}")
    print(f"Traceback: {error_trace}")
    
    app = FastAPI(title="NeuroDigest API - Error Mode")
    
    @app.get("/")
    def root():
        return {
            "status": "error",
            "message": "App initialization failed",
            "error": import_error,
            "note": "Check Vercel function logs for full traceback"
        }
    
    @app.get("/health")
    def health():
        return {"status": "error", "message": import_error}
    
    @app.get("/debug")
    def debug():
        import os
        db_url = os.getenv("DATABASE_URL", "NOT SET")
        # Show first and last 10 chars for security
        if db_url != "NOT SET":
            db_url_display = f"{db_url[:10]}...{db_url[-10:]}" if len(db_url) > 20 else "***"
        else:
            db_url_display = "NOT SET"
        return {
            "error": import_error,
            "database_url_set": db_url != "NOT SET",
            "database_url_preview": db_url_display
        }

# CRITICAL: Ensure app is defined for Vercel detection
if app is None:
    app = FastAPI()
    @app.get("/")
    def fallback():
        return {"error": "App not initialized"}

# Export for Vercel (explicit)
__all__ = ['app']
