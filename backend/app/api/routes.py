from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_orchestrator, get_session, get_settings, get_store
from app.config import Settings
from app.core.errors import ApiError
from app.core.orchestrator import Orchestrator
from app.core.sessions import Session, SessionStore, SourceRecord
from app.core.validation import MEDIA, ingest_upload
from app.schemas import (
    AnalysisResult, AnalyzeRequest, DeleteResult, RedactRequest, SessionCreated, SessionInfo, SourceInfo,
)

router = APIRouter(prefix="/api/v1")

_SLACK = 1024 * 1024  # phần dư cho multipart overhead


def _info(r: SourceRecord) -> SourceInfo:
    return SourceInfo(source_id=r.source_id, source_version=r.version, filename=r.filename,
                      detected_type=r.detected_type, size_bytes=r.size_bytes, sha256=r.sha256,
                      type_mismatch=r.type_mismatch, mismatch_reasons=r.mismatch_reasons,
                      supported_features=r.supported_features)


def _precheck_length(request: Request, settings: Settings) -> None:
    """Từ chối sớm theo Content-Length. Chỉ là lớp 1 (client có thể nói dối): giới hạn thật nằm trong ingest_upload,
    và khi deploy nên đặt thêm giới hạn body ở reverse proxy."""
    try:
        declared = int(request.headers.get("content-length", "0"))
    except ValueError:
        declared = 0
    if declared > settings.max_upload_bytes + _SLACK:
        raise ApiError(413, "FILE_TOO_LARGE", f"File exceeds the {settings.max_upload_bytes // (1024 * 1024)} MB limit.")


@router.post("/sessions", response_model=SessionCreated, status_code=201)
def create_session(store: SessionStore = Depends(get_store)) -> SessionCreated:
    s, token = store.create()
    return SessionCreated(session_id=s.session_id, access_token=token, created_at=s.created_at, expires_at=s.expires_at)


@router.get("/sessions/{session_id}", response_model=SessionInfo)
def get_session_info(session: Session = Depends(get_session)) -> SessionInfo:
    return SessionInfo(session_id=session.session_id, created_at=session.created_at, expires_at=session.expires_at,
                       sources=[_info(r) for r in session.sources.values()])


@router.delete("/sessions/{session_id}", response_model=DeleteResult)
def delete_session(session: Session = Depends(get_session), store: SessionStore = Depends(get_store)) -> DeleteResult:
    return store.delete(session)


@router.post("/sessions/{session_id}/sources", response_model=SourceInfo, status_code=201)
async def upload_source(request: Request, file: UploadFile = File(...), session: Session = Depends(get_session),
                        store: SessionStore = Depends(get_store), settings: Settings = Depends(get_settings)) -> SourceInfo:
    _precheck_length(request, settings)
    store.ensure_can_add_source(session)
    source_id = secrets.token_hex(8)
    dest = store.source_path(session.session_id, source_id, 1)
    ing = await ingest_upload(file, dest, settings.max_upload_bytes)
    return _info(store.add_source(session, source_id, ing, dest))


@router.put("/sessions/{session_id}/sources/{source_id}", response_model=SourceInfo)
async def replace_source(source_id: str, request: Request, file: UploadFile = File(...),
                         session: Session = Depends(get_session), store: SessionStore = Depends(get_store),
                         settings: Settings = Depends(get_settings)) -> SourceInfo:
    _precheck_length(request, settings)
    old = session.sources.get(source_id)
    if old is None:
        raise ApiError(404, "SOURCE_NOT_FOUND", "File not found in this session.")
    dest = store.source_path(session.session_id, source_id, old.version + 1)
    ing = await ingest_upload(file, dest, settings.max_upload_bytes)
    return _info(store.replace_source(session, source_id, old.version, ing, dest))


@router.get("/sessions/{session_id}/sources/{source_id}/content")
def source_content(source_id: str, session: Session = Depends(get_session)) -> FileResponse:
    """Cho frontend render PDF/ảnh khi review vùng redact. Chỉ phục vụ pdf/png/jpeg đã nhất quán loại."""
    rec = session.sources.get(source_id)
    if rec is None:
        raise ApiError(404, "SOURCE_NOT_FOUND", "File not found in this session.")
    if rec.detected_type not in MEDIA or rec.type_mismatch:
        raise ApiError(415, "UNSUPPORTED_TYPE", "This file type cannot be previewed.")
    return FileResponse(rec.path, media_type=MEDIA[rec.detected_type][0], headers={"Content-Disposition": "inline"})


@router.post("/sessions/{session_id}/analyze", response_model=AnalysisResult)
async def analyze(req: AnalyzeRequest, session: Session = Depends(get_session),
                  orch: Orchestrator = Depends(get_orchestrator)) -> AnalysisResult:
    return await orch.analyze(session, req)


@router.post("/sessions/{session_id}/redact", response_model=AnalysisResult)
async def redact(req: RedactRequest, session: Session = Depends(get_session),
                 orch: Orchestrator = Depends(get_orchestrator)) -> AnalysisResult:
    return await orch.redact(session, req)


@router.get("/sessions/{session_id}/results", response_model=list[AnalysisResult])
def list_results(session: Session = Depends(get_session)) -> list[AnalysisResult]:
    return list(session.results.values())


@router.get("/sessions/{session_id}/outputs/{output_id}")
def download_output(output_id: str, session: Session = Depends(get_session)) -> FileResponse:
    """Chỉ output đã được orchestrator phát hành (verification == pass) mới tải được."""
    rec = session.outputs.get(output_id)
    if rec is None or not rec.path.is_file():
        raise ApiError(404, "OUTPUT_NOT_FOUND", "Output not found.")
    return FileResponse(rec.path, media_type=rec.media_type, filename=f"redacted-{output_id}.{rec.ext}")
