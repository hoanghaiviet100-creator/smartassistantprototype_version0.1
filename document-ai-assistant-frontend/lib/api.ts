import type {
  ApiChatRequest,
  ApiChatResponse,
  ApiDocument,
  ApiDocumentListResponse,
} from "@/types";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new Error(
      `Cannot reach the backend at ${API_BASE_URL}. Start the FastAPI server and try again.`,
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null) as
      | { detail?: string; message?: string }
      | null;
    throw new ApiError(
      body?.detail ?? body?.message ?? `Request failed (${response.status}).`,
      response.status,
    );
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

/** Upload file bytes to the future FastAPI endpoint. Not connected to the UI yet. */
export function uploadDocument(file: File): Promise<ApiDocument> {
  const formData = new FormData();
  formData.append("file", file);
  return request<ApiDocument>("/api/v1/documents", {
    method: "POST",
    body: formData,
  });
}

/** List documents stored by the backend. */
export async function getDocuments(): Promise<ApiDocument[]> {
  const response = await request<ApiDocumentListResponse>("/api/v1/documents");
  return response.items;
}

/** Retrieve processing status for one document. */
export function getDocument(documentId: string): Promise<ApiDocument> {
  return request<ApiDocument>(`/api/v1/documents/${encodeURIComponent(documentId)}`);
}

/** Delete a document and its indexed chunks on the backend. */
export function deleteDocument(documentId: string): Promise<void> {
  return request<void>(`/api/v1/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
  });
}

/** Ask the backend RAG endpoint. */
export function sendChat(payload: ApiChatRequest): Promise<ApiChatResponse> {
  return request<ApiChatResponse>("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
