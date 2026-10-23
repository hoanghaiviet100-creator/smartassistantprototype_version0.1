"""F1 — Scam & Phishing Assessment.   OWNER: Role 3

Input : ctx.text (đã giới hạn độ dài) HOẶC ctx.source (PNG/JPEG -> OCR, giữ lại text gốc để kiểm quote).
Output: AnalysisResult(feature=F1, risk_band=..., findings=[...], next_action=...)

TODO (theo report, P3/P4/P5):
- Chuẩn hoá text; OCR ảnh; nếu OCR lỗi/trống -> status=PARTIAL/FAILED, risk_band=INSUFFICIENT (không bao giờ LOW).
- Rule: urgency, đòi tiền/OTP/mật khẩu, mạo danh, URL đáng ngờ -> Finding(feature=F1, category=..., source=RULE).
- Mỗi evidence (nếu có LLM) phải khớp nguyên văn trong text nguồn; risk_band tính BẰNG CODE, LLM không được set.
- masked_evidence luôn đã mask; không log nội dung.
"""
from app.features.base import AnalysisContext, not_implemented
from app.schemas import AnalysisResult


def analyze(ctx: AnalysisContext) -> AnalysisResult:
    return not_implemented(ctx)
