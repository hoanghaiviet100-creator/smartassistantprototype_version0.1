"""F3 — Pre-open File Scan.   OWNER: Role 6

Input : ctx.source — file xử lý như DỮ LIỆU, không bao giờ thực thi. detected_type/size/sha256 đã có sẵn từ lúc upload.
Output: AnalysisResult(feature=F3, verdict=..., detected_type, size_bytes, sha256, coverage.engines)

TODO:
- Từ ctx.source.mismatch_reasons tạo Finding(category=TYPE_MISMATCH) (đã tính ở P2).
- ClamAV (clamd) trong worker cô lập, có timeout. Engine vắng/timeout/parser lỗi -> status=PARTIAL, verdict=UNKNOWN
  ("Unable to fully scan"); ghi coverage.engines = {"clamav": "not_run" | "failed" | "complete"}.
- Không bao giờ trả "safe". NO_DETECTIONS chỉ hợp lệ khi status=COMPLETE (schema sẽ từ chối nếu không).
"""
from app.features.base import AnalysisContext, not_implemented
from app.schemas import AnalysisResult


def analyze(ctx: AnalysisContext) -> AnalysisResult:
    return not_implemented(ctx)
