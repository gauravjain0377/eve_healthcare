"""
Vercel Serverless Entry Point for EVE Healthcare API.
Vercel's Python runtime will load the ASGI FastAPI app from this module.
"""
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.main import app

# Export app and handler for Vercel ASGI runtime
handler = app
__all__ = ["app", "handler"]
