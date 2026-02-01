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

from mangum import Mangum

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

# Wrap FastAPI app with Mangum for AWS Lambda/Vercel compatibility
# lifespan="off" because serverless functions don't support startup/shutdown events properly
handler = Mangum(app, lifespan="off")
