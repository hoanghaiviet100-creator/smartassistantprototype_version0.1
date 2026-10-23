# DocuMind — Privacy & File Security Assistant

```
smartassistantprototype_version0.1/
├── document-ai-assistant-frontend/   # Next.js 15 + TypeScript (UI)
└── backend/                          # FastAPI (API, orchestrator, F1–F4)
```

Chạy local (2 terminal):

```bash
# 1) backend  → http://localhost:8000/docs
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# 2) frontend → http://localhost:3000
cd document-ai-assistant-frontend && npm install && cp .env.example .env.local && npm run dev
```

Chi tiết backend, quy ước và phân công file: [`backend/README.md`](backend/README.md).
