"""
Session + source version + vòng đời lưu trữ (P8, phần nền; Role 7 mở rộng cleanup/report).

- session_id công khai, access_token bí mật (chỉ lưu SHA-256, so sánh constant-time). Sai token, hết hạn,
  không tồn tại đều trả cùng một 404 để không lộ session nào đang tồn tại.
- expires_at = created_at + TTL, KHÔNG gia hạn khi có hoạt động mới.
- Xoá lỗi thì session bị "đóng băng" (không truy cập được) và job purge thử lại; không báo đã xoá khi chưa xoá.
- State nằm trong RAM: chạy 1 worker. Khởi động/tắt máy sẽ xoá sạch thư mục sess_* còn sót.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from app.config import Settings
from app.core.errors import ApiError
from app.core.validation import MEDIA, IngestedFile
from app.schemas import AnalysisResult, DeleteResult, Feature

log = logging.getLogger("documind.sessions")

_DIR_PREFIX = "sess_"  # wipe_all chỉ đụng vào thư mục có tiền tố này
_OUTPUT_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_NOT_FOUND = ("SESSION_NOT_FOUND", "Session not found or expired.")


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class SourceRecord:
    source_id: str
    version: int
    filename: str
    path: Path
    size_bytes: int
    sha256: str
    detected_type: str
    mismatch_reasons: list[str]
    supported_features: list[Feature]

    @property
    def type_mismatch(self) -> bool:
        return bool(self.mismatch_reasons)


@dataclass
class OutputRecord:
    source_id: str
    path: Path
    media_type: str
    ext: str


@dataclass
class Session:
    session_id: str
    token_hash: str
    created_at: int
    expires_at: int
    sources: dict[str, SourceRecord] = field(default_factory=dict)
    results: dict[tuple[str, str], AnalysisResult] = field(default_factory=dict)  # (f"{feature}:{kind}", source_id)
    outputs: dict[str, OutputRecord] = field(default_factory=dict)  # chỉ output ĐÃ verify pass
    cleanup_error: Optional[str] = None


class SessionStore:
    def __init__(self, settings: Settings, clock: Callable[[], float] = time.time) -> None:
        self._settings = settings
        self._clock = clock
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    # ----- helpers -----
    def now(self) -> int:
        return int(self._clock())

    def _dir(self, session_id: str) -> Path:
        return self._settings.storage_dir / f"{_DIR_PREFIX}{session_id}"

    def source_path(self, session_id: str, source_id: str, version: int) -> Path:
        d = self._dir(session_id)
        d.mkdir(mode=0o700, parents=True, exist_ok=True)
        return d / f"src_{source_id}_v{version}.bin"  # đuôi .bin: không bao giờ chạy được nhầm

    def output_path(self, session_id: str, output_id: str) -> Path:
        """Role 5 ghi file đã redact vào ĐÚNG đường dẫn này để nó bị dọn cùng session."""
        if not _OUTPUT_ID.match(output_id):
            raise ValueError("invalid output_id")
        d = self._dir(session_id)
        d.mkdir(mode=0o700, parents=True, exist_ok=True)
        return d / f"out_{output_id}.bin"

    # ----- lifecycle -----
    def create(self) -> tuple[Session, str]:
        self.purge_expired()
        with self._lock:
            if len(self._sessions) >= self._settings.max_sessions:
                raise ApiError(429, "TOO_MANY_SESSIONS", "The server is busy. Try again later.")
            now = self.now()
            token = secrets.token_urlsafe(32)
            s = Session(secrets.token_urlsafe(24), _hash(token), now, now + self._settings.session_ttl_seconds)
            self._sessions[s.session_id] = s
        log.info("session_created id=%s", s.session_id[:8])
        return s, token

    def authenticate(self, session_id: str, token: Optional[str]) -> Session:
        with self._lock:
            s = self._sessions.get(session_id)
            if s is None or s.cleanup_error or not token:
                raise ApiError(404, *_NOT_FOUND)
            if not hmac.compare_digest(_hash(token), s.token_hash):
                raise ApiError(404, *_NOT_FOUND)
            if self.now() >= s.expires_at:
                self._delete_locked(s)
                raise ApiError(404, *_NOT_FOUND)
            return s

    def delete(self, session: Session) -> DeleteResult:
        with self._lock:
            err = self._delete_locked(session)
        return DeleteResult(deleted=err is None, cleanup_error=err)

    def _delete_locked(self, s: Session) -> Optional[str]:
        path = self._dir(s.session_id)
        try:
            if path.exists():
                shutil.rmtree(path)
            if path.exists():
                raise OSError("directory still present")
        except OSError:
            s.cleanup_error = "CLEANUP_FAILED"  # đóng băng session, purge sẽ thử lại
            log.error("cleanup_failed id=%s", s.session_id[:8])
            return s.cleanup_error
        s.sources.clear(); s.results.clear(); s.outputs.clear()
        self._sessions.pop(s.session_id, None)
        log.info("session_deleted id=%s", s.session_id[:8])
        return None

    def purge_expired(self) -> tuple[int, int]:
        """Trả về (đã xoá, xoá lỗi). Gọi định kỳ từ main.py; cũng thử lại các session bị lỗi cleanup."""
        deleted = failed = 0
        with self._lock:
            now = self.now()
            for s in list(self._sessions.values()):
                if s.cleanup_error or now >= s.expires_at:
                    if self._delete_locked(s) is None:
                        deleted += 1
                    else:
                        failed += 1
        return deleted, failed

    def wipe_all(self) -> None:
        """Khi khởi động/tắt: xoá mọi sess_* (state RAM đã mất nên file còn sót là rác)."""
        with self._lock:
            self._sessions.clear()
        root = self._settings.storage_dir
        if root.is_dir():
            for child in root.iterdir():
                if child.name.startswith(_DIR_PREFIX):
                    shutil.rmtree(child, ignore_errors=True)

    # ----- sources -----
    def ensure_can_add_source(self, session: Session) -> None:
        if len(session.sources) >= self._settings.max_sources_per_session:
            raise ApiError(409, "TOO_MANY_SOURCES", "This session reached its file limit.")

    def _record(self, source_id: str, version: int, ing: IngestedFile, path: Path) -> SourceRecord:
        return SourceRecord(source_id, version, ing.filename, path, ing.size_bytes, ing.sha256,
                            ing.detected_type, ing.mismatch_reasons, ing.supported_features)

    def add_source(self, session: Session, source_id: str, ing: IngestedFile, path: Path) -> SourceRecord:
        with self._lock:
            if self._sessions.get(session.session_id) is not session or session.cleanup_error:
                path.unlink(missing_ok=True)
                raise ApiError(404, *_NOT_FOUND)
            rec = self._record(source_id, 1, ing, path)
            session.sources[source_id] = rec
            return rec

    def replace_source(self, session: Session, source_id: str, expected_version: int,
                       ing: IngestedFile, path: Path) -> SourceRecord:
        """Thay file => version+1, xoá kết quả/output suy ra từ bản cũ (không để kết quả cũ gắn vào file mới)."""
        with self._lock:
            old = session.sources.get(source_id)
            if (self._sessions.get(session.session_id) is not session or session.cleanup_error
                    or old is None or old.version != expected_version):
                path.unlink(missing_ok=True)
                raise ApiError(409, "SOURCE_CONFLICT", "The file changed while uploading. Retry.")
            rec = self._record(source_id, old.version + 1, ing, path)
            session.sources[source_id] = rec
            old.path.unlink(missing_ok=True)
            for key in [k for k in session.results if k[1] == source_id]:
                del session.results[key]
            for oid in [o for o, r in session.outputs.items() if r.source_id == source_id]:
                session.outputs.pop(oid).path.unlink(missing_ok=True)
            return rec

    # ----- results / outputs -----
    def save_result(self, session: Session, result: AnalysisResult, kind: str = "analyze") -> None:
        with self._lock:
            session.results[(f"{result.feature.value}:{kind}", result.source_id)] = result

    def get_result(self, session: Session, feature: Feature, source_id: str, kind: str = "analyze") -> Optional[AnalysisResult]:
        return session.results.get((f"{feature.value}:{kind}", source_id))

    def release_output(self, session: Session, source: SourceRecord, output_id: str, path: Path) -> None:
        media, ext = MEDIA.get(source.detected_type, ("application/octet-stream", "bin"))
        with self._lock:
            session.outputs[output_id] = OutputRecord(source.source_id, path, media, ext)
