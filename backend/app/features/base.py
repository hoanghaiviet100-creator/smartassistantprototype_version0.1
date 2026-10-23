"""
Hợp đồng chung giữa orchestrator và module của từng role.

Mỗi analyzer là một hàm ĐỒNG BỘ  `analyze(ctx) -> AnalysisResult`  (OCR/CPU nặng chạy trong thread).
Orchestrator tự ghi đè session_id/source_id/source_version/feature nên analyzer không cần (và không thể)
đổi các trường đó. Analyzer chỉ cần trả findings, coverage, errors và các trường riêng của feature.

Luật chung:
- Chưa chạy / lỗi / không phát hiện là 3 trạng thái KHÁC NHAU. Không bao giờ biến thiếu dữ liệu thành "sạch".
- Không đưa nội dung người dùng vào ErrorInfo.message hay log.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from app.config import Settings
from app.core.sessions import SourceRecord
from app.schemas import AnalysisResult, ErrorInfo, Feature, Finding, RiskBand, RunStatus, Verdict

TEXT_SOURCE_ID = "text"  # source_id quy ước cho F1 khi người dùng dán text (không có file)


@dataclass(frozen=True)
class AnalysisContext:
    session_id: str
    feature: Feature
    source: Optional[SourceRecord]  # có path tới file (đọc, KHÔNG thực thi); None nếu F1 nhận text
    text: Optional[str]  # F1: text dán vào
    settings: Settings

    @property
    def source_id(self) -> str:
        return self.source.source_id if self.source else TEXT_SOURCE_ID

    @property
    def source_version(self) -> int:
        return self.source.version if self.source else 1


Analyzer = Callable[[AnalysisContext], AnalysisResult]
Redactor = Callable[[AnalysisContext, list[Finding]], AnalysisResult]


def empty_result(ctx: AnalysisContext, status: RunStatus, errors: Iterable[ErrorInfo] = ()) -> AnalysisResult:
    """Kết quả hợp lệ với mặc định AN TOÀN (F1 = insufficient, F3 = unknown). Dùng cho stub và khi lỗi."""
    extra: dict = {}
    if ctx.feature == Feature.SCAM:
        extra["risk_band"] = RiskBand.INSUFFICIENT
    if ctx.feature == Feature.FILE_SCAN:
        extra["verdict"] = Verdict.UNKNOWN
        if ctx.source:
            extra.update(detected_type=ctx.source.detected_type, size_bytes=ctx.source.size_bytes, sha256=ctx.source.sha256)
    return AnalysisResult(
        session_id=ctx.session_id, source_id=ctx.source_id, source_version=ctx.source_version,
        feature=ctx.feature, status=status, errors=list(errors), **extra,
    )


def not_implemented(ctx: AnalysisContext) -> AnalysisResult:
    err = ErrorInfo(code="NOT_IMPLEMENTED", message=f"{ctx.feature.value} is not implemented yet.")
    return empty_result(ctx, RunStatus.NOT_RUN, [err])
