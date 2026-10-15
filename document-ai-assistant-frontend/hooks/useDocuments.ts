"use client";

import { useMemo, useState } from "react";
import type { DocumentKind, SourceDocument } from "@/types";

const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;

const sampleDocuments: SourceDocument[] = [
  {
    id: "sample-1",
    name: "Student handbook.pdf",
    size: "2.4 MB",
    kind: "pdf",
    status: "sample",
  },
  {
    id: "sample-2",
    name: "Research notes.pdf",
    size: "840 KB",
    kind: "pdf",
    status: "sample",
  },
];

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getDocumentKind(file: File): DocumentKind | null {
  if (file.type === "application/pdf" || /\.pdf$/i.test(file.name)) return "pdf";
  if (
    file.type === "image/png" ||
    file.type === "image/jpeg" ||
    /\.(png|jpe?g)$/i.test(file.name)
  ) return "image";
  return null;
}

export function useDocuments() {
  const [documents, setDocuments] = useState<SourceDocument[]>(sampleDocuments);
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState(
    "Demo mode · Files stay in local UI state; backend upload and RAG are not connected.",
  );

  const visibleDocuments = useMemo(
    () => documents.filter((document) =>
      document.name.toLowerCase().includes(search.toLowerCase()),
    ),
    [documents, search],
  );

  function addFiles(fileList: FileList | File[] | null): void {
    if (!fileList || fileList.length === 0) return;

    const accepted: File[] = [];
    const rejected: string[] = [];

    for (const file of Array.from(fileList)) {
      const kind = getDocumentKind(file);
      if (!kind) {
        rejected.push(`${file.name}: unsupported type`);
      } else if (file.size > MAX_FILE_SIZE_BYTES) {
        rejected.push(`${file.name}: larger than 20 MB`);
      } else {
        accepted.push(file);
      }
    }

    const additions: SourceDocument[] = accepted.map((file) => ({
      id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 9)}`,
      name: file.name,
      size: formatSize(file.size),
      sizeBytes: file.size,
      kind: getDocumentKind(file) ?? "image",
      // Local means the file was selected in this browser only, not uploaded or indexed.
      status: "local",
    }));

    if (additions.length > 0) {
      setDocuments((current) => [...additions, ...current]);
    }

    const noticeParts: string[] = [];
    if (additions.length > 0) {
      noticeParts.push(
        `${additions.length} file(s) added to the UI demo only. No upload, OCR, or indexing has run.`,
      );
    }
    if (rejected.length > 0) {
      noticeParts.push(`Rejected: ${rejected.join("; ")}.`);
    }
    setNotice(noticeParts.join(" ") || "No files were added.");
  }

  return {
    documents,
    visibleDocuments,
    search,
    setSearch,
    notice,
    setNotice,
    addFiles,
    sampleCount: documents.filter((document) => document.status === "sample").length,
    localCount: documents.filter((document) => document.status === "local").length,
    readyCount: documents.filter((document) => document.status === "ready").length,
    processingCount: documents.filter((document) => document.status === "processing").length,
  };
}
