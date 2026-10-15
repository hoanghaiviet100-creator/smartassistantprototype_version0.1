export type DocumentKind = "pdf" | "image";

export type DocumentStatus = "sample" | "local" | "processing" | "ready" | "failed";

export interface SourceDocument {
  id: string;
  name: string;
  size: string;
  sizeBytes?: number;
  kind: DocumentKind;
  status: DocumentStatus;
}

export interface Citation {
  documentId: string;
  filename: string;
  pageNumber?: number;
  chunkId?: string;
  excerpt: string;
}

export type MessageRole = "assistant" | "user";
export type MessageOrigin = "welcome" | "mock" | "api";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  citations?: Citation[];
  origin?: MessageOrigin;
}

export interface ApiDocument {
  id: string;
  filename: string;
  size_bytes: number;
  status: "processing" | "ready" | "error" | "failed";
  error?: string;
}

export interface ApiDocumentListResponse {
  items: ApiDocument[];
}

export interface ApiChatRequest {
  question: string;
  document_ids: string[];
}

export interface ApiCitation {
  document_id: string;
  filename: string;
  page_number?: number;
  chunk_id?: string;
  excerpt: string;
}

export interface ApiChatResponse {
  answer: string;
  citations: ApiCitation[];
}
