"""Vercel serverless entry point for the Grant Tracker API."""
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.api import app

# Vercel expects the ASGI app to be named 'app' or 'handler'
handler = app
