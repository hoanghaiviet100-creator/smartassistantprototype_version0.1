# DocuMind backend (FastAPI)

Python **3.11+**. Chạy **1 worker** (session nằm trong RAM).

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload                         # Swagger: http://localhost:8000/docs
uvicorn app.main:app --reload --env-file .env         # nếu muốn dùng .env (copy từ .env.example)
python -m pytest -q
```

## Ai sở hữu file nào (mỗi người chỉ sửa file của mình để tránh conflict)

| File | Owner | Việc |
|---|---|---|
| `app/schemas.py` (+ `types/documind.ts` ở frontend) | Role 1 | Hợp đồng dữ liệu. Sửa → cập nhật cả 2 file + tăng `SCHEMA_VERSION` |
| `app/main.py`, `app/api/*`, `app/core/*`, `app/config.py` | Role 1 | Skeleton, upload P1/P2, session, orchestrator |
| `app/features/f1_scam.py` | Role 3 | F1 |
| `app/features/f2_detect.py` | Role 4 | F2a: extract/OCR/detect |
| `app/features/f2_redact.py` | Role 5 | F2b: redact + verify |
| `app/features/f3_filescan.py` | Role 6 | F3 (+ cô lập worker, ClamAV) |
| `app/core/sessions.py` (cleanup), report | Role 7 | F4: retention, xoá, report, log |

Mỗi feature là **một hàm** nhận `AnalysisContext`, trả `AnalysisResult` (xem docstring đầu mỗi file). Hiện đều là stub trả `status=not_run` — cố ý **không** trả "sạch".

## Luồng API (`/api/v1`, mọi route sau `POST /sessions` cần header `X-Session-Token`)

| Method | Path | Việc |
|---|---|---|
| POST | `/sessions` | Tạo session → `session_id`, `access_token` (chỉ trả 1 lần), `expires_at` (= tạo + 6h) |
| GET / DELETE | `/sessions/{sid}` | Xem session + danh sách file / xoá sớm (`cleanup_error` nếu xoá lỗi) |
| POST | `/sessions/{sid}/sources` | Upload (multipart, field `file`) → `SourceInfo` (loại theo magic bytes, cờ mismatch, feature hỗ trợ) |
| PUT | `/sessions/{sid}/sources/{id}` | Thay file → `source_version` +1, kết quả/output cũ bị xoá |
| GET | `/sessions/{sid}/sources/{id}/content` | Lấy lại pdf/png/jpeg để frontend render khi review vùng redact |
| POST | `/sessions/{sid}/analyze` | `{feature: F1/F2/F3, source_id \| text, expected_source_version?}` → `AnalysisResult` |
| POST | `/sessions/{sid}/redact` | `{source_id, source_version, confirmed_finding_ids[, rejected_finding_ids]}` → `AnalysisResult` |
| GET | `/sessions/{sid}/results` | Mọi kết quả của session (F4 dùng để dựng report) |
| GET | `/sessions/{sid}/outputs/{output_id}` | Tải file đã redact — chỉ khi `verification == pass` |

Luồng F2: upload → `analyze(F2)` → người dùng review → `redact` → tải output. Lỗi trả `{"detail": "...", "code": "..."}`.

## Những gì orchestrator đã đảm bảo sẵn
- Upload: stream xuống đĩa, giới hạn size, tên file sanitize, không bao giờ thực thi; file mismatch (ext/MIME ≠ magic bytes) chỉ được đi vào F3.
- Analyzer crash / timeout / trả sai schema → `status=failed` + mã lỗi, không lộ traceback hay nội dung.
- F3 chưa quét xong mà báo `no_detections`, hoặc có `redacted_output_id` mà chưa `pass` → bị schema từ chối.
- Session: token bí mật, hết hạn cố định 6h từ lúc tạo, xoá lỗi thì đóng băng + thử lại, khởi động/tắt máy dọn sạch file.

## Giới hạn đã biết (ghi vào report, đừng "claim" hơn)
- Timeout dùng thread nên không kill được tác vụ đang chạy; cô lập thật (process/container, không network) là việc của Role 6.
- State trong RAM: restart = mất session (file bị xoá). Chưa có xác thực người dùng; chỉ có token theo session.
- Giới hạn size thật nên đặt thêm ở reverse proxy; check `Content-Length` chỉ là lớp đầu.
- Polyglot file vẫn qua được kiểm tra loại; xoá file không đảm bảo erase khỏi backup/swap.
