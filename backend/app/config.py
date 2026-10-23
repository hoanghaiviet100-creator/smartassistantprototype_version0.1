"""Cấu hình đọc từ biến môi trường (xem backend/.env.example). Không cần thư viện ngoài."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _num(name: str, default, cast):
    raw = os.getenv(name)
    return cast(raw) if raw else default


@dataclass(frozen=True)
class Settings:
    storage_dir: Path = Path(".data/sessions")
    max_upload_bytes: int = 15 * 1024 * 1024  # report: 15 MB là mức đề xuất
    session_ttl_seconds: int = 6 * 3600  # report: mục tiêu lưu trữ 6 giờ, tính từ lúc TẠO session
    max_sessions: int = 200
    max_sources_per_session: int = 5
    max_text_chars: int = 20_000  # F1 text dán vào
    analyze_timeout_seconds: float = 60.0
    purge_interval_seconds: float = 60.0
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        return cls(
            storage_dir=Path(os.getenv("STORAGE_DIR", ".data/sessions")).resolve(),
            max_upload_bytes=_num("MAX_UPLOAD_MB", 15, int) * 1024 * 1024,
            session_ttl_seconds=_num("SESSION_TTL_SECONDS", 6 * 3600, int),
            max_sessions=_num("MAX_SESSIONS", 200, int),
            max_sources_per_session=_num("MAX_SOURCES_PER_SESSION", 5, int),
            max_text_chars=_num("MAX_TEXT_CHARS", 20_000, int),
            analyze_timeout_seconds=_num("ANALYZE_TIMEOUT_SECONDS", 60.0, float),
            purge_interval_seconds=_num("PURGE_INTERVAL_SECONDS", 60.0, float),
            cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        )
