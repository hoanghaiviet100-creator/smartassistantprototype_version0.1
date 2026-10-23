"""
P1 Untrusted Upload Isolation + P2 Multi-Attribute File-Type Check.

Nguyên tắc: file upload là DỮ LIỆU, không bao giờ được thực thi/import. Tên file từ client không
được dùng làm đường dẫn. Loại file lấy từ magic bytes; extension + MIME client gửi chỉ để so sánh.

Giới hạn đã biết (ghi rõ trong report): polyglot file vẫn qua được check này; kiểm tra cấu trúc
không chứng minh file vô hại; phát hiện "text" chỉ dựa trên 4 KB đầu.
"""
from __future__ import annotations

import codecs
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from app.core.errors import ApiError
from app.schemas import Feature

HEAD_BYTES = 4096
CHUNK = 1024 * 1024

_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"PK\x03\x04", "zip"),  # gồm cả docx/xlsx/pptx
    (b"MZ", "exe"),
    (b"\x7fELF", "elf"),
)

_EXT_TYPE = {
    "pdf": "pdf", "png": "png", "jpg": "jpeg", "jpeg": "jpeg", "gif": "gif",
    "zip": "zip", "docx": "zip", "xlsx": "zip", "pptx": "zip",
    "exe": "exe", "dll": "exe", "txt": "text", "csv": "text", "md": "text",
}
_MIME_TYPE = {
    "application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpeg", "image/gif": "gif",
    "application/zip": "zip", "text/plain": "text", "text/csv": "text",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "zip",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "zip",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "zip",
}
_EXEC_EXT = {"exe", "dll", "scr", "bat", "cmd", "com", "js", "vbs", "ps1", "jar", "msi"}
_DOC_EXT = {"pdf", "png", "jpg", "jpeg", "gif", "doc", "docx", "xls", "xlsx", "txt"}

# Loại file mỗi feature xử lý được. F3 nhận mọi loại (đó là mục đích của nó).
_FEATURE_TYPES = {Feature.SCAM: {"png", "jpeg"}, Feature.SENSITIVE: {"pdf", "png", "jpeg"}}

# Loại được phép trả lại inline / tải về (chống XSS: không phục vụ html, svg...)
MEDIA = {"pdf": ("application/pdf", "pdf"), "png": ("image/png", "png"), "jpeg": ("image/jpeg", "jpg")}

_CTRL = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True)
class IngestedFile:
    filename: str
    size_bytes: int
    sha256: str
    detected_type: str
    mismatch_reasons: list[str]
    supported_features: list[Feature]


def sanitize_filename(raw: str | None) -> str:
    name = (raw or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = _CTRL.sub("", name).strip().strip(".")
    return name[:120] or "upload"


def _looks_like_text(head: bytes) -> bool:
    if not head or b"\x00" in head:
        return False
    try:  # incremental decoder chịu được ký tự UTF-8 bị cắt ở cuối đoạn đầu
        codecs.getincrementaldecoder("utf-8")().decode(head, final=False)
        return True
    except UnicodeDecodeError:
        return False


def detect_type(head: bytes) -> str:
    for sig, name in _MAGIC:
        if head.startswith(sig):
            return name
    return "text" if _looks_like_text(head) else "unknown"


def check_type_consistency(filename: str, claimed_mime: str | None, detected: str) -> list[str]:
    reasons: list[str] = []
    parts = filename.lower().split(".")
    ext = parts[-1] if len(parts) > 1 else ""
    expected = _EXT_TYPE.get(ext)
    if expected and expected != detected:
        reasons.append("extension_mismatch")
    mime = (claimed_mime or "").split(";")[0].strip().lower()
    expected_mime = _MIME_TYPE.get(mime)  # octet-stream/không rõ -> không có kỳ vọng
    if expected_mime and expected_mime != detected:
        reasons.append("mime_mismatch")
    if len(parts) > 2 and parts[-1] in _EXEC_EXT and parts[-2] in _DOC_EXT:
        reasons.append("double_extension")
    return reasons


def supported_features(detected: str, mismatch_reasons: list[str]) -> list[Feature]:
    """Chính sách: file bị mismatch KHÔNG đưa vào F1/F2 (không tin được loại), chỉ F3 (quét trước khi mở)."""
    feats = [f for f, types in _FEATURE_TYPES.items() if not mismatch_reasons and detected in types]
    return feats + [Feature.FILE_SCAN]


async def ingest_upload(
    upload: UploadFile, dest: Path, max_bytes: int
) -> IngestedFile:
    """Stream upload xuống `dest` (quyền 0600), vừa đọc vừa kiểm size/hash; không đọc cả file vào RAM."""
    tmp = dest.with_suffix(".part")
    digest = hashlib.sha256()
    size = 0
    head = b""
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await upload.read(CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise ApiError(413, "FILE_TOO_LARGE", f"File exceeds the {max_bytes // (1024 * 1024)} MB limit.")
                if len(head) < HEAD_BYTES:
                    head += chunk[: HEAD_BYTES - len(head)]
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise ApiError(400, "EMPTY_FILE", "The uploaded file is empty.")
        os.replace(tmp, dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    filename = sanitize_filename(upload.filename)
    detected = detect_type(head)
    reasons = check_type_consistency(filename, upload.content_type, detected)
    return IngestedFile(filename, size, digest.hexdigest(), detected, reasons, supported_features(detected, reasons))
