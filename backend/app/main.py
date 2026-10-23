from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import Settings
from app.core.errors import ApiError
from app.core.orchestrator import Orchestrator
from app.core.sessions import SessionStore
from app.features.base import Analyzer, Redactor
from app.schemas import Feature

log = logging.getLogger("documind")


async def _purge_loop(store: SessionStore, interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(store.purge_expired)
        except Exception as exc:  # noqa: BLE001
            log.error("purge_failed exc=%s", type(exc).__name__)


def create_app(settings: Optional[Settings] = None, analyzers: Optional[dict[Feature, Analyzer]] = None,
               redactor: Optional[Redactor] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = SessionStore(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store.wipe_all()  # state nằm trong RAM: file còn sót từ lần chạy trước là rác
        task = asyncio.create_task(_purge_loop(store, settings.purge_interval_seconds))
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            store.wipe_all()

    app = FastAPI(title="DocuMind API", version="1.1", lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.state.orchestrator = Orchestrator(store, settings, analyzers, redactor)

    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["X-Session-Token", "Content-Type"],
    )

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Không echo "input" của pydantic: có thể chứa nội dung nhạy cảm người dùng vừa gửi
        errors = [{"loc": [str(p) for p in e["loc"]], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": "Invalid request.", "code": "VALIDATION_ERROR", "errors": errors})

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(router)
    return app


app = create_app()
