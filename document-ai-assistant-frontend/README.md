# DocuMind — Document AI Assistant (Frontend starter)

Frontend-first prototype for a document question-answering app. Built with Next.js, React, TypeScript, and CSS.

## Current status

This is **UI-only scaffolding**. Uploading a file currently updates local UI state; it does not upload file bytes, run OCR, create embeddings, retrieve chunks, or call an LLM. Chat responses and citations are explicitly simulated.

## Requirements

- Node.js 20.9+ (recommended)
- npm

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Supported file types in the UI

- PDF
- PNG
- JPG / JPEG

The 20 MB limit is currently presentation copy only; add actual client-side and server-side validation when wiring the API.

## Next integration steps

1. Create the FastAPI backend.
2. Add `POST /api/v1/documents` for multipart upload.
3. Add `GET /api/v1/documents` for the user's document list and processing status.
4. Add `POST /api/v1/chat` accepting `{ question, document_ids }`.
5. Return answer text plus citations such as `{ document_id, filename, page_number, chunk_id, excerpt }`.
6. Replace local mock handlers in `app/page.tsx` with API calls using `NEXT_PUBLIC_API_BASE_URL`.
7. Add loading, retry, empty, and error states.

## Suggested API contract

### `POST /api/v1/documents`

`multipart/form-data`, field `file`

Response:
```json
{
  "id": "doc_123",
  "filename": "handbook.pdf",
  "size_bytes": 245760,
  "status": "processing"
}
```

### `GET /api/v1/documents`

Response:
```json
{
  "items": [
    {
      "id": "doc_123",
      "filename": "handbook.pdf",
      "size_bytes": 245760,
      "status": "ready"
    }
  ]
}
```

### `POST /api/v1/chat`

Request:
```json
{
  "question": "What is the deadline?",
  "document_ids": ["doc_123"]
}
```

Response:
```json
{
  "answer": "The deadline is ...",
  "citations": [
    {
      "document_id": "doc_123",
      "filename": "handbook.pdf",
      "page_number": 12,
      "chunk_id": "chunk_42",
      "excerpt": "..."
    }
  ]
}
```
