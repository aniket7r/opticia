"""Session API endpoints."""

from fastapi import APIRouter, HTTPException

from app.models.session import Session
from app.services.session_service import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=Session)
async def create_session() -> Session:
    """Create a new session."""
    return await session_service.create()


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str) -> Session:
    """Get session by ID."""
    session = await session_service.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/end", response_model=Session)
async def end_session(session_id: str) -> Session:
    """End a session."""
    session = await session_service.end(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("", response_model=list[Session])
async def list_sessions(active_only: bool = False, limit: int = 50) -> list[Session]:
    """List sessions."""
    if active_only:
        return await session_service.list_active()
    return await session_service.list_recent(limit=limit)
