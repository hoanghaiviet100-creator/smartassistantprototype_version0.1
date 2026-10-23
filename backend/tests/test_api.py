from __future__ import annotations

import time

from app.features.base import AnalysisContext, empty_result
from app.schemas import (
    AnalysisResult, BBox, Category, Feature, Finding, Location, RedactionResult, RunStatus, Source,
    VerificationStatus, Verdict,
)
from tests.conftest import PDF, PNG, Sess


# ---------- phiên & quyền truy cập ----------
def test_health_and_session_flow(client):
    assert client.get("/health").json() == {"ok": True}
    r = client.post("/api/v1/sessions")
    assert r.status_code == 201 and r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["expires_at"] - body["created_at"] == 6 * 3600
    s = Sess(client)
    assert client.get(s.base, headers=s.h).json()["sources"] == []


def test_token_required_and_wrong_token_is_404(client, sess):
    assert client.get(sess.base).status_code == 404
    assert client.get(sess.base, headers={"X-Session-Token": "bad"}).status_code == 404
    other = Sess(client)
    assert client.get(sess.base, headers=other.h).status_code == 404  # token của session khác


def test_delete_session_revokes_access_and_removes_files(client, sess, settings):
    sess.upload(PDF, "a.pdf", "application/pdf")
    assert any(settings.storage_dir.iterdir())
    r = client.delete(sess.base, headers=sess.h)
    assert r.json() == {"deleted": True, "cleanup_error": None}
    assert client.get(sess.base, headers=sess.h).status_code == 404
    assert not any(settings.storage_dir.iterdir())


# ---------- upload P1/P2 ----------
def test_upload_detects_type_and_hashes(sess):
    r = sess.upload(PNG, "../../evil/photo.png", "image/png")
    b = r.json()
    assert r.status_code == 201 and b["detected_type"] == "png" and b["filename"] == "photo.png"
    assert b["source_version"] == 1 and len(b["sha256"]) == 64 and b["type_mismatch"] is False
    assert b["supported_features"] == ["F1", "F2", "F3"]


def test_upload_too_large_empty_and_limits(client, sess):
    assert sess.upload(b"A" * (1024 * 1024 + 1), "big.bin").status_code == 413
    assert sess.upload(b"", "e.pdf").status_code == 400
    assert not any(p.suffix == ".part" for p in client.app.state.settings.storage_dir.rglob("*"))  # không để file tạm
    for i in range(5):
        assert sess.upload(PNG, f"{i}.png").status_code == 201
    assert sess.upload(PNG, "6.png").status_code == 409


def test_mismatch_is_flagged_and_blocks_f1_f2_but_not_f3(sess):
    b = sess.upload(PNG, "report.pdf", "application/pdf").json()  # PNG đội lốt .pdf
    assert b["type_mismatch"] is True and b["supported_features"] == ["F3"]
    sid = b["source_id"]
    assert sess.analyze(feature="F2", source_id=sid).status_code == 415
    assert sess.analyze(feature="F3", source_id=sid).status_code == 200


def test_source_content_only_for_safe_types(client, sess):
    pdf = sess.upload(PDF, "a.pdf", "application/pdf").json()["source_id"]
    r = client.get(f"{sess.base}/sources/{pdf}/content", headers=sess.h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    z = sess.upload(b"PK\x03\x04" + b"0" * 30, "a.zip").json()["source_id"]
    assert client.get(f"{sess.base}/sources/{z}/content", headers=sess.h).status_code == 415


# ---------- stub trung thực ----------
def test_stubs_report_not_run_never_clean(sess):
    png = sess.upload(PNG, "a.png", "image/png").json()["source_id"]
    f3 = sess.analyze(feature="F3", source_id=png).json()
    assert f3["status"] == "not_run" and f3["verdict"] == "unknown" and f3["detected_type"] == "png"
    f2 = sess.analyze(feature="F2", source_id=png).json()
    assert f2["status"] == "not_run" and f2["findings"] == []
    f1 = sess.analyze(feature="F1", text="Tài khoản của bạn sẽ bị khoá, gửi OTP ngay").json()
    assert f1["status"] == "not_run" and f1["risk_band"] == "insufficient" and f1["source_id"] == "text"


def test_input_validation_per_feature(sess):
    png = sess.upload(PNG, "a.png", "image/png").json()["source_id"]
    assert sess.analyze(feature="F1").status_code == 422
    assert sess.analyze(feature="F1", text="hi", source_id=png).status_code == 422
    assert sess.analyze(feature="F1", text="   ").status_code == 422
    assert sess.analyze(feature="F1", text="x" * 20_001).status_code == 413
    assert sess.analyze(feature="F3").status_code == 422
    assert sess.analyze(feature="F3", source_id="nope").status_code == 404
    r = sess.analyze(feature="F9")
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR" and "input" not in r.text


def test_replace_bumps_version_and_drops_stale_results(client, sess):
    sid = sess.upload(PDF, "a.pdf", "application/pdf").json()["source_id"]
    assert sess.analyze(feature="F2", source_id=sid).status_code == 200
    assert len(client.get(f"{sess.base}/results", headers=sess.h).json()) == 1
    r = client.put(f"{sess.base}/sources/{sid}", headers=sess.h, files={"file": ("a.pdf", PDF + b"more", "application/pdf")})
    assert r.json()["source_version"] == 2
    assert client.get(f"{sess.base}/results", headers=sess.h).json() == []
    assert sess.analyze(feature="F2", source_id=sid, expected_source_version=1).status_code == 409
    assert sess.analyze(feature="F2", source_id=sid, expected_source_version=2).status_code == 200


# ---------- orchestrator với analyzer giả ----------
def finding(i="f1", bbox=True):
    return Finding(id=i, feature=Feature.SENSITIVE, category=Category.PHONE, source=Source.REGEX, confidence=0.9,
                   masked_evidence="09******21", location=Location(page=1, bbox=BBox(x0=.1, y0=.1, x1=.3, y1=.2) if bbox else None))


def fake_detect(ctx: AnalysisContext) -> AnalysisResult:
    r = empty_result(ctx, RunStatus.COMPLETE)
    return r.model_copy(update={"findings": [finding("f1"), finding("f2", bbox=False)]})


def test_analyzer_crash_timeout_and_invalid_result_become_failed(make_client):
    def crash(ctx): raise RuntimeError("secret text 0912345678")
    def slow(ctx): time.sleep(0.5); return empty_result(ctx, RunStatus.COMPLETE)
    def liar(ctx):  # F3 chưa quét xong mà báo NO_DETECTIONS
        return empty_result(ctx, RunStatus.PARTIAL).model_copy(update={"verdict": Verdict.NO_DETECTIONS})
    def wrong_type(ctx): return {"not": "a result"}

    for fn, code in ((crash, "ANALYZER_CRASH"), (slow, "TIMEOUT"), (liar, "INVALID_RESULT"), (wrong_type, "INVALID_RESULT")):
        c = make_client(analyzers={Feature.FILE_SCAN: fn, Feature.SCAM: crash, Feature.SENSITIVE: crash},
                        settings={"analyze_timeout_seconds": 0.1})
        s = Sess(c)
        sid = s.upload(PNG, "a.png", "image/png").json()["source_id"]
        r = s.analyze(feature="F3", source_id=sid)
        body = r.json()
        assert r.status_code == 200 and body["status"] == "failed" and body["errors"][0]["code"] == code
        assert body["verdict"] == "unknown" and "secret" not in r.text


def test_analyzer_cannot_forge_identity(make_client):
    def forger(ctx):
        return empty_result(ctx, RunStatus.COMPLETE).model_copy(update={"session_id": "other", "source_version": 99})
    c = make_client(analyzers={Feature.SENSITIVE: forger, Feature.SCAM: forger, Feature.FILE_SCAN: forger})
    s = Sess(c)
    sid = s.upload(PDF, "a.pdf", "application/pdf").json()["source_id"]
    body = s.analyze(feature="F2", source_id=sid).json()
    assert body["session_id"] == s.id and body["source_version"] == 1


def _redact(s, **kw):
    return s.c.post(f"{s.base}/redact", headers=s.h, json=kw)


def test_redact_review_rules(make_client):
    c = make_client(analyzers={Feature.SENSITIVE: fake_detect, Feature.SCAM: fake_detect, Feature.FILE_SCAN: fake_detect})
    s = Sess(c)
    sid = s.upload(PDF, "a.pdf", "application/pdf").json()["source_id"]
    assert _redact(s, source_id=sid, source_version=1, confirmed_finding_ids=["f1"]).status_code == 409  # chưa detect
    s.analyze(feature="F2", source_id=sid)
    assert _redact(s, source_id=sid, source_version=2, confirmed_finding_ids=["f1"]).status_code == 409  # sai version
    assert _redact(s, source_id=sid, source_version=1, confirmed_finding_ids=[]).status_code == 422
    assert _redact(s, source_id=sid, source_version=1, confirmed_finding_ids=["zzz"]).json()["code"] == "UNKNOWN_FINDING"
    assert _redact(s, source_id=sid, source_version=1, confirmed_finding_ids=["f2"]).json()["code"] == "FINDING_NOT_REDACTABLE"
    assert _redact(s, source_id=sid, source_version=1, confirmed_finding_ids=["f1"], rejected_finding_ids=["f1"]).json()["code"] == "CONFLICTING_REVIEW"


def test_redact_release_only_when_verified(make_client):
    state = {"verification": VerificationStatus.PASS_, "write": True}

    def redactor(ctx, findings):
        assert [f.id for f in findings] == ["f1"] and all(f.review.value == "confirmed" for f in findings)
        if state["write"]:
            (ctx.settings.storage_dir / f"sess_{ctx.session_id}" / "out_o1.bin").write_bytes(b"%PDF-redacted")
        r = empty_result(ctx, RunStatus.COMPLETE)
        v = state["verification"]
        return r.model_copy(update={"redaction": RedactionResult(
            redacted_output_id="o1" if v == VerificationStatus.PASS_ else None,
            applied_region_count=len(findings), verification=v, residual_count=0 if v == VerificationStatus.PASS_ else None)})

    c = make_client(analyzers={Feature.SENSITIVE: fake_detect, Feature.SCAM: fake_detect, Feature.FILE_SCAN: fake_detect}, redactor=redactor)
    s = Sess(c)
    sid = s.upload(PDF, "a.pdf", "application/pdf").json()["source_id"]
    s.analyze(feature="F2", source_id=sid)
    url = f"{s.base}/outputs/o1"

    # 1) verify FAIL => không có output để tải
    state["verification"] = VerificationStatus.FAIL
    body = _redact(s, source_id=sid, source_version=1, confirmed_finding_ids=["f1"]).json()
    assert body["redaction"]["verification"] == "fail" and body["redaction"]["redacted_output_id"] is None
    assert c.get(url, headers=s.h).status_code == 404

    # 2) PASS nhưng file không tồn tại => OUTPUT_MISSING, không phát hành
    for leftover in c.app.state.settings.storage_dir.rglob("out_o1.bin"):
        leftover.unlink()  # bước 1 đã ghi file; xoá để mô phỏng redactor không tạo file
    state.update(verification=VerificationStatus.PASS_, write=False)
    body = _redact(s, source_id=sid, source_version=1, confirmed_finding_ids=["f1"]).json()
    assert body["status"] == "failed" and body["errors"][0]["code"] == "OUTPUT_MISSING"
    assert c.get(url, headers=s.h).status_code == 404

    # 3) PASS + file thật => tải được; sau khi review, finding f1 được lưu là confirmed
    state["write"] = True
    body = _redact(s, source_id=sid, source_version=1, confirmed_finding_ids=["f1"], rejected_finding_ids=["f2"]).json()
    assert body["redaction"]["verification"] == "pass" and body["redaction"]["residual_count"] == 0
    d = c.get(url, headers=s.h)
    assert d.status_code == 200 and d.content == b"%PDF-redacted" and d.headers["content-type"] == "application/pdf"
    saved = {f["id"]: f["review"] for r in c.get(f"{s.base}/results", headers=s.h).json() if r["feature"] == "F2" for f in r["findings"]}
    assert saved == {"f1": "confirmed", "f2": "rejected"}

    # 4) thay file nguồn => output cũ bị thu hồi
    assert c.put(f"{s.base}/sources/{sid}", headers=s.h, files={"file": ("a.pdf", PDF + b"2", "application/pdf")}).status_code == 200
    assert c.get(url, headers=s.h).status_code == 404


def test_schema_rejects_output_id_without_pass():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RedactionResult(redacted_output_id="o1", verification=VerificationStatus.INCONCLUSIVE)
    RedactionResult(redacted_output_id="o1", verification=VerificationStatus.PASS_)
