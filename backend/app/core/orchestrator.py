"""
Orchestrator: nối Validated input -> F1 | F2 (detect -> user confirm -> redact) | F3 -> lưu kết quả cho F4.

Việc nó đảm bảo (để các role không phải tự nhớ):
- Kiểm đầu vào theo feature + loại file được hỗ trợ (415), kiểm source_version (409).
- Ghi đè session_id/source_id/source_version/feature trong kết quả; validate lại bằng schema.
- Analyzer crash/timeout/trả sai schema => AnalysisResult(status=FAILED) với mã lỗi, KHÔNG lộ traceback/nội dung.
- Redact chỉ chạy với finding id đã tồn tại trong kết quả detect MỚI NHẤT, có bbox, và đúng source_version.
- File redact chỉ được "phát hành" (tải về được) khi schema xác nhận verification == PASS và file thật sự tồn tại.

Giới hạn: timeout dùng thread nên KHÔNG kill được thread đang chạy; cô lập thật sự (process/container,
không network) là việc của Role 6 (P1 hardening).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from pydantic import ValidationError

from app.config import Settings
from app.core.errors import ApiError
from app.core.sessions import Session, SessionStore, SourceRecord
from app.features import ANALYZERS, REDACTOR
from app.features.base import AnalysisContext, Analyzer, Redactor, empty_result
from app.schemas import (
    AnalysisResult, AnalyzeRequest, ErrorInfo, Feature, Finding, RedactRequest, ReviewStatus, RunStatus,
)

log = logging.getLogger("documind.orchestrator")


class Orchestrator:
    def __init__(self, store: SessionStore, settings: Settings,
                 analyzers: Optional[dict[Feature, Analyzer]] = None, redactor: Optional[Redactor] = None) -> None:
        self.store = store
        self.settings = settings
        self.analyzers = analyzers or ANALYZERS
        self.redactor = redactor or REDACTOR

    # ---------- analyze (F1 / F2 detect / F3) ----------
    async def analyze(self, session: Session, req: AnalyzeRequest) -> AnalysisResult:
        source = self._source(session, req.source_id, req.expected_source_version)
        self._check_inputs(req, source)
        ctx = AnalysisContext(session.session_id, req.feature, source, req.text, self.settings)
        result = await self._run(ctx, self.analyzers[req.feature])
        self.store.save_result(session, result)
        return result

    def _source(self, session: Session, source_id: Optional[str], expected: Optional[int]) -> Optional[SourceRecord]:
        if source_id is None:
            return None
        rec = session.sources.get(source_id)
        if rec is None:
            raise ApiError(404, "SOURCE_NOT_FOUND", "File not found in this session.")
        if expected is not None and rec.version != expected:
            raise ApiError(409, "SOURCE_VERSION_MISMATCH", "The file changed since it was reviewed. Re-run the analysis.")
        return rec

    def _check_inputs(self, req: AnalyzeRequest, source: Optional[SourceRecord]) -> None:
        if req.feature == Feature.SCAM:
            if (req.text is None) == (source is None):
                raise ApiError(422, "INVALID_INPUT", "Provide either text or an image file for F1, not both or neither.")
            if req.text is not None:
                if not req.text.strip():
                    raise ApiError(422, "EMPTY_TEXT", "The text is empty.")
                if len(req.text) > self.settings.max_text_chars:
                    raise ApiError(413, "TEXT_TOO_LARGE", f"Text exceeds {self.settings.max_text_chars} characters.")
        elif source is None:
            raise ApiError(422, "MISSING_SOURCE", f"{req.feature.value} requires source_id.")
        if source is not None and req.feature not in source.supported_features:
            raise ApiError(415, "UNSUPPORTED_TYPE", f"{req.feature.value} does not support this file (type or consistency check).")

    # ---------- redact (F2b) ----------
    async def redact(self, session: Session, req: RedactRequest) -> AnalysisResult:
        source = self._source(session, req.source_id, req.source_version)
        assert source is not None
        if Feature.SENSITIVE not in source.supported_features:
            raise ApiError(415, "UNSUPPORTED_TYPE", "F2 does not support this file.")
        detection = self.store.get_result(session, Feature.SENSITIVE, source.source_id)
        if detection is None or detection.source_version != source.version:
            raise ApiError(409, "NO_CURRENT_DETECTION", "Run F2 detection on the current file version first.")

        confirmed = list(dict.fromkeys(req.confirmed_finding_ids))
        rejected = list(dict.fromkeys(req.rejected_finding_ids))
        by_id = {f.id: f for f in detection.findings}
        if set(confirmed) & set(rejected):
            raise ApiError(422, "CONFLICTING_REVIEW", "A finding cannot be both confirmed and rejected.")
        if any(i not in by_id for i in confirmed + rejected):
            raise ApiError(422, "UNKNOWN_FINDING", "Unknown finding id.")
        if any(not (by_id[i].location and by_id[i].location.bbox) for i in confirmed):
            raise ApiError(422, "FINDING_NOT_REDACTABLE", "A confirmed finding has no region (bbox).")

        # Lưu trạng thái review; id không được nhắc tới giữ nguyên (chưa quyết định => không redact)
        reviewed = [
            f.model_copy(update={"review": ReviewStatus.CONFIRMED if f.id in confirmed
                                 else ReviewStatus.REJECTED if f.id in rejected else f.review})
            for f in detection.findings
        ]
        self.store.save_result(session, detection.model_copy(update={"findings": reviewed}))

        ctx = AnalysisContext(session.session_id, Feature.SENSITIVE, source, None, self.settings)
        result = await self._run(ctx, self.redactor, [by_id[i].model_copy(update={"review": ReviewStatus.CONFIRMED}) for i in confirmed])

        red = result.redaction
        if red is not None and red.redacted_output_id:
            try:
                path = self.store.output_path(session.session_id, red.redacted_output_id)
            except ValueError:
                path = None
            if path is not None and path.is_file():
                self.store.release_output(session, source, red.redacted_output_id, path)
            else:
                result = self._failed(ctx, "OUTPUT_MISSING", "The redacted file was not produced.")
        self.store.save_result(session, result, kind="redact")
        return result

    # ---------- chạy analyzer an toàn ----------
    async def _run(self, ctx: AnalysisContext, fn: Any, *args: Any) -> AnalysisResult:
        try:
            raw = await asyncio.wait_for(asyncio.to_thread(fn, ctx, *args), timeout=self.settings.analyze_timeout_seconds)
        except TimeoutError:
            log.error("analyzer_timeout feature=%s", ctx.feature.value)
            return self._failed(ctx, "TIMEOUT", "Processing timed out.")
        except Exception as exc:  # noqa: BLE001 - cố ý: không để traceback (có thể chứa nội dung) lọt ra ngoài
            log.error("analyzer_crash feature=%s exc=%s", ctx.feature.value, type(exc).__name__)
            return self._failed(ctx, "ANALYZER_CRASH", "Processing failed unexpectedly.")
        return self._normalise(ctx, raw)

    def _normalise(self, ctx: AnalysisContext, raw: Any) -> AnalysisResult:
        if not isinstance(raw, AnalysisResult):
            return self._failed(ctx, "INVALID_RESULT", "Processing returned an invalid result.")
        data = raw.model_dump()
        data.update(session_id=ctx.session_id, source_id=ctx.source_id, source_version=ctx.source_version, feature=ctx.feature)
        try:
            return AnalysisResult.model_validate(data)
        except ValidationError:
            log.error("invalid_result feature=%s", ctx.feature.value)
            return self._failed(ctx, "INVALID_RESULT", "Processing returned an invalid result.")

    def _failed(self, ctx: AnalysisContext, code: str, message: str) -> AnalysisResult:
        return empty_result(ctx, RunStatus.FAILED, [ErrorInfo(code=code, message=message)])
