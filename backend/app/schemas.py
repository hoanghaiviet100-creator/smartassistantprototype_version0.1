"""
DocuMind shared schema v1  (backend/app/schemas.py)

Quy ước bắt buộc cho cả team:
- Toạ độ BBox: chuẩn hoá 0..1, gốc TOP-LEFT, y hướng xuống, tính trên trang
  SAU KHI áp dụng rotation (đúng như người dùng nhìn thấy). page đánh số từ 1.
- Chỉ lưu masked_evidence (vd "09******21"). KHÔNG đưa text gốc vào schema này.
- Phân biệt rõ: NOT_RUN / FAILED / UNSUPPORTED / NO_DETECTIONS. Thiếu dữ liệu != sạch.
- confidence là heuristic 0..1, không phải xác suất đã hiệu chỉnh.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.1"


# ---------- Enums ----------
class Feature(StrEnum):
    SCAM = "F1"
    SENSITIVE = "F2"
    FILE_SCAN = "F3"


class Category(StrEnum):
    # F1 signals
    URGENCY = "urgency"
    MONEY_REQUEST = "money_request"
    CREDENTIAL_REQUEST = "credential_request"  # OTP, mật khẩu...
    IMPERSONATION = "impersonation"
    SUSPICIOUS_URL = "suspicious_url"
    # F2 sensitive data
    EMAIL = "email"
    PHONE = "phone"
    NATIONAL_ID = "national_id"  # CCCD/CMND
    CARD_NUMBER = "card_number"
    OTHER_ID = "other_id"
    # F3 file scan
    TYPE_MISMATCH = "type_mismatch"
    MALWARE_SIGNATURE = "malware_signature"
    STRUCTURE_ANOMALY = "structure_anomaly"


class Source(StrEnum):
    REGEX = "regex"
    VALIDATOR = "validator"
    OCR = "ocr"
    PDF_TEXT = "pdf_text"
    RULE = "rule"
    CLAMAV = "clamav"
    MAGIC = "magic"
    LLM = "llm"  # chỉ để giải thích, KHÔNG quyết định severity


class ReviewStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"  # người dùng xác nhận redact
    REJECTED = "rejected"


class RunStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"  # một phần trang/engine lỗi -> "unable to fully scan"
    FAILED = "failed"
    NOT_RUN = "not_run"


class PageStatus(StrEnum):
    SCANNED = "scanned"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"
    NOT_RUN = "not_run"


class VerificationStatus(StrEnum):
    FAIL = "fail"
    PASS_ = "pass"
    INCONCLUSIVE = "inconclusive"
    NOT_RUN = "not_run"


class RiskBand(StrEnum):  # F1
    INSUFFICIENT = "insufficient"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Verdict(StrEnum):  # F3 — không có "safe"
    UNKNOWN = "unknown"
    NO_DETECTIONS = "no_detections"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"


# ---------- Core ----------
class BBox(BaseModel):
    model_config = ConfigDict(frozen=True)
    x0: float = Field(ge=0, le=1)
    y0: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _ordered(self) -> "BBox":
        if not (self.x0 < self.x1 and self.y0 < self.y1):
            raise ValueError("bbox must satisfy x0<x1 and y0<y1")
        return self


class Location(BaseModel):
    page: int = Field(ge=1)
    bbox: Optional[BBox] = None  # F2 bắt buộc nếu muốn redact
    char_start: Optional[int] = Field(default=None, ge=0)  # offset trong text đã chuẩn hoá (F1/F2)
    char_end: Optional[int] = Field(default=None, ge=0)


class Finding(BaseModel):
    id: str  # uuid4, sinh ở backend
    feature: Feature
    category: Category
    source: Source
    confidence: float = Field(ge=0, le=1)
    masked_evidence: str  # đã mask, vd "09******21". Không bao giờ là raw
    location: Optional[Location] = None  # F3 / F1 dạng text có thể None
    note: Optional[str] = None  # giải thích ngắn (từ rule hoặc LLM)
    review: ReviewStatus = ReviewStatus.PENDING  # chỉ F2 dùng

    @model_validator(mode="after")
    def _redactable_needs_bbox(self) -> "Finding":
        if self.review == ReviewStatus.CONFIRMED and self.feature == Feature.SENSITIVE:
            if not (self.location and self.location.bbox):
                raise ValueError("confirmed F2 finding requires location.bbox")
        return self


# ---------- Coverage / errors ----------
class PageCoverage(BaseModel):
    page: int = Field(ge=1)
    status: PageStatus
    method: Optional[str] = None  # "pdf_text" | "ocr"
    error_code: Optional[str] = None  # vd "OCR_TIMEOUT"; không chứa nội dung file


class Coverage(BaseModel):
    pages: list[PageCoverage] = []
    engines: dict[str, RunStatus] = {}  # vd {"clamav": "not_run", "magic": "complete"}
    limits: list[str] = []  # vd ["max_pages=20", "max_size_mb=15"]


class ErrorInfo(BaseModel):
    code: str  # vd "PARSER_FAILURE"
    message: str  # KHÔNG chứa nội dung người dùng


# ---------- Redaction verification (F2b -> F4) ----------
class RedactionResult(BaseModel):
    redacted_output_id: Optional[str] = None  # chỉ set khi verification = pass
    applied_region_count: int = 0
    verification: VerificationStatus = VerificationStatus.NOT_RUN
    residual_count: Optional[int] = None  # None = unknown (KHÁC 0)

    @model_validator(mode="after")
    def _release_only_if_verified(self) -> "RedactionResult":
        # Policy của report: withhold file nếu verification fail/inconclusive/not_run
        if self.redacted_output_id and self.verification != VerificationStatus.PASS_:
            raise ValueError("redacted_output_id requires verification == pass")
        return self


# ---------- Envelope: mọi module trả về cái này ----------
class AnalysisResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    session_id: str  # random, không đoán được
    source_id: str
    source_version: int = 1  # tăng khi file nguồn đổi; redact phải khớp version
    feature: Feature
    status: RunStatus
    findings: list[Finding] = []
    coverage: Coverage = Coverage()
    errors: list[ErrorInfo] = []
    # F1 only
    risk_band: Optional[RiskBand] = None  # tính bằng code, không do LLM
    next_action: Optional[str] = None
    # F2 only
    redaction: Optional[RedactionResult] = None
    # F3 only
    verdict: Optional[Verdict] = None
    detected_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None

    @model_validator(mode="after")
    def _invariants(self) -> "AnalysisResult":
        if self.feature == Feature.SCAM and self.status != RunStatus.COMPLETE:
            if self.risk_band not in (None, RiskBand.INSUFFICIENT):
                raise ValueError("incomplete F1 run must be INSUFFICIENT")
        if self.feature == Feature.FILE_SCAN:
            if self.status != RunStatus.COMPLETE and self.verdict == Verdict.NO_DETECTIONS:
                raise ValueError("incomplete F3 scan cannot be NO_DETECTIONS")
        return self


# ---------- F4 ----------
class TemporaryReport(BaseModel):
    report_id: str
    session_id: str
    created_at: int  # unix seconds, thời điểm tạo SESSION
    expires_at: int  # = created_at + 6h (mục tiêu)
    verification: VerificationStatus = VerificationStatus.NOT_RUN
    finding_count: int = 0
    deleted: bool = False
    cleanup_error: Optional[str] = None  # có lỗi thì KHÔNG được báo "đã xoá hoàn toàn"


# ---------- API models (v1.1) ----------
class SessionCreated(BaseModel):
    session_id: str
    access_token: str  # gửi lại qua header X-Session-Token; chỉ trả đúng 1 lần
    created_at: int
    expires_at: int


class SourceInfo(BaseModel):
    source_id: str
    source_version: int
    filename: str  # đã sanitize, chỉ để hiển thị
    detected_type: str  # pdf|png|jpeg|gif|zip|exe|elf|text|unknown (từ magic bytes)
    size_bytes: int
    sha256: str
    type_mismatch: bool
    mismatch_reasons: list[str] = []  # extension_mismatch | mime_mismatch | double_extension
    supported_features: list[Feature]


class SessionInfo(BaseModel):
    session_id: str
    created_at: int
    expires_at: int
    sources: list[SourceInfo] = []


class DeleteResult(BaseModel):
    deleted: bool
    cleanup_error: Optional[str] = None  # có lỗi thì KHÔNG được báo "đã xoá hoàn toàn"


class AnalyzeRequest(BaseModel):
    feature: Feature
    source_id: Optional[str] = None  # F2/F3 bắt buộc; F1 dùng source_id (ảnh) HOẶC text
    text: Optional[str] = None  # F1: nội dung dán vào
    expected_source_version: Optional[int] = Field(default=None, ge=1)


class RedactRequest(BaseModel):
    source_id: str
    source_version: int = Field(ge=1)  # phải khớp version đã detect + review
    confirmed_finding_ids: list[str] = Field(min_length=1)
    rejected_finding_ids: list[str] = []  # id không nằm trong 2 list = chưa quyết định, KHÔNG redact
