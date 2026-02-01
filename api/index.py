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
except Exception as e:
    # Import failed - create fallback app
    import_error = str(e)
    app = FastAPI(title="NeuroDigest API")
    
    @app.get("/")
    def root():
        return {
            "status": "error",
            "message": "App initialization failed",
            "error": import_error
        }
    
    @app.get("/health")
    def health():
        return {"status": "error", "message": import_error}

# CRITICAL: Ensure app is defined for Vercel detection
if app is None:
    app = FastAPI()
    @app.get("/")
    def fallback():
        return {"error": "App not initialized"}

# Export for Vercel (explicit)
__all__ = ['app']
