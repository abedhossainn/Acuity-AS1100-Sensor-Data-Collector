"""API routes."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["core"])


@router.get("/status")
async def status():
    """Get API status."""
    return {"status": "ready"}
