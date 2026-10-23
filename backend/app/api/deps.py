from __future__ import annotations

from typing import Optional

from fastapi import Header, Request

from app.config import Settings
from app.core.orchestrator import Orchestrator
from app.core.sessions import Session, SessionStore


def get_store(request: Request) -> SessionStore:
    return request.app.state.store


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def get_session(request: Request, session_id: str, x_session_token: Optional[str] = Header(default=None)) -> Session:
    """Mọi route /sessions/{session_id}/... đều đi qua đây: kiểm token + hết hạn."""
    return request.app.state.store.authenticate(session_id, x_session_token)
