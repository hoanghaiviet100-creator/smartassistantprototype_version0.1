# DocuMind — Document AI Assistant

Frontend scaffold for a document question-answering application. Built with Next.js, React, TypeScript, and CSS.

## Current status

This repository is currently a **frontend-only UI prototype**. The UI is organized into feature-based React components. Document selection and chat interactions still run in local demo mode.

- Selecting a file adds its metadata to local React state only.
- Files are **not uploaded to a server**, OCR is not run, and chunks/embeddings are not created.
- Chat submission does **not** call an LLM or run retrieval. The UI explicitly shows a demo-mode notice instead of fabricating an answer or citation.
- Sample document rows are illustrative and are not indexed data.
- `lib/api.ts` defines the future FastAPI client functions but they are not wired into the UI yet.

## Requirements

- Node.js 20.9+ (Node.js 22 LTS is suitable)
- npm

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000.

## Available scripts

```bash
npm run dev       # Next.js development server
npm run lint      # ESLint
npm run typecheck # TypeScript type checking
npm run build     # Production build
```

## Frontend structure

```text
app/
  layout.tsx
  page.tsx                 # Compose the page and connect hooks/components
  globals.css
components/
  layout/                   # Sidebar, Topbar
  chat/                     # MessageList, MessageBubble, ChatComposer, SuggestedQuestions
  documents/                # DocumentList, DocumentItem, UploadDropzone
  sources/                  # KnowledgeSourcesPanel, CitationCard
hooks/
  useDocuments.ts           # Local document UI state and client-side validation
  useChat.ts                # Local chat state; demo-only response
lib/
  api.ts                    # Typed fetch wrapper and future FastAPI functions

types/
  index.ts                  # Shared UI and API contracts
```

## Frontend environment

`.env.example` includes:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

This variable only sets the base URL for the typed API client; the UI is not connected to that API yet. Do not put model-provider API keys in `NEXT_PUBLIC_*` variables because they are exposed to the browser.

## API contract prepared for the backend

### `POST /api/v1/documents`

`multipart/form-data`, field `file`. Expected response:

```json
{
  "id": "doc_123",
  "filename": "handbook.pdf",
  "size_bytes": 245760,
  "status": "processing"
}
```

### `GET /api/v1/documents`

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

### `GET /api/v1/documents/{id}`

Returns the document and its current processing status.

### `DELETE /api/v1/documents/{id}`

Deletes a document and its indexed chunks.

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

The backend must be the source of truth for file validation, processing status, retrieval, and citations. Client-side validation is for user feedback only.

## Next milestone

Implement the FastAPI health endpoint and real multipart file upload with server-side validation and local storage. Then implement PDF extraction/OCR and chunk metadata before adding embeddings and RAG retrieval.
