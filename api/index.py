"""
Vercel serverless function wrapper for FastAPI app.
This file makes the FastAPI app compatible with Vercel's serverless functions.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import app - this will trigger DB initialization attempt
try:
    from mcp_server.main import app
except Exception as e:
    # If import fails, create a minimal error app
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    def error():
        return {"error": f"App initialization failed: {str(e)}"}

# Vercel Python runtime automatically detects 'app' variable
# For serverless compatibility, we also create a handler using Mangum
# But Vercel will use 'app' directly for FastAPI
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    # Mangum not available - Vercel will use app directly
    handler = app
