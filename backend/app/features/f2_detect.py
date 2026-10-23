"""F2a — Trích text/OCR + phát hiện dữ liệu nhạy cảm.   OWNER: Role 4

Input : ctx.source (pdf/png/jpeg đã qua P1/P2).
Output: AnalysisResult(feature=F2, findings=[Finding(location=Location(page, bbox)...)], coverage=...)

TODO:
- Trích text PDF (kèm toạ độ), OCR ảnh; dùng BBox CHUẨN HOÁ 0..1, gốc top-left, đã tính rotation (xem schemas.BBox).
- Regex + validator: email, SĐT VN, CCCD, số thẻ (Luhn) -> Finding(source=REGEX|VALIDATOR), masked_evidence đã mask.
- coverage.pages: trang nào SCANNED / FAILED / UNSUPPORTED. Trang lỗi KHÔNG được coi là sạch (status=PARTIAL).
- Giữ giới hạn trang/size trong coverage.limits.
"""
from app.features.base import AnalysisContext, not_implemented
from app.schemas import AnalysisResult


def analyze(ctx: AnalysisContext) -> AnalysisResult:
    return not_implemented(ctx)
