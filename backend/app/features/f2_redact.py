"""F2b — Redact vùng đã được người dùng xác nhận + verify.   OWNER: Role 5

Input : ctx.source + `findings` = CHỈ các Finding đã confirmed (orchestrator đã kiểm id/bbox/version).
Output: AnalysisResult(feature=F2, redaction=RedactionResult(...))

TODO:
- PDF: xoá nội dung thật bên dưới (không chỉ vẽ đè). Ảnh: burn pixel đặc vào ảnh mới.
- Ghi output vào  store.output_path(session_id, output_id)  (hoặc tính đường dẫn tương đương trong cùng thư mục session).
- Mở lại output, trích text/OCR lại vùng đã redact -> residual_count (None = chưa biết, KHÁC 0).
- Chỉ đặt redacted_output_id khi verification == PASS (schema sẽ từ chối nếu không).
"""
from app.features.base import AnalysisContext, empty_result
from app.schemas import AnalysisResult, ErrorInfo, Finding, RedactionResult, RunStatus, VerificationStatus


def redact(ctx: AnalysisContext, findings: list[Finding]) -> AnalysisResult:
    result = empty_result(ctx, RunStatus.NOT_RUN, [ErrorInfo(code="NOT_IMPLEMENTED", message="F2 redaction is not implemented yet.")])
    return result.model_copy(update={"redaction": RedactionResult(verification=VerificationStatus.NOT_RUN)})
