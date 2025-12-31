"""Vercel serverless entry point for FastAPI app."""

from backend.main import app

# Vercel expects this name
app = app
