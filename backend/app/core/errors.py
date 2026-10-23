from __future__ import annotations


class ApiError(Exception):
    """Lỗi có chủ đích. Trả JSON {"detail": message, "code": code} — khớp lib/api.ts của frontend (đọc body.detail)."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
