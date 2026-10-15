import { Check, FileImage, FileText, XCircle } from "lucide-react";
import type { SourceDocument } from "@/types";

type Variant = "sidebar" | "source";

interface DocumentItemProps {
  document: SourceDocument;
  variant: Variant;
  selected?: boolean;
  onSelect?: (documentId: string) => void;
}

function getStatusLabel(status: SourceDocument["status"], size: string): string {
  switch (status) {
    case "sample":
      return `Sample data · ${size}`;
    case "local":
      return `${size} · Local demo only`;
    case "processing":
      return `${size} · Processing`;
    case "failed":
      return `${size} · Failed`;
    case "ready":
      return `${size} · Ready`;
  }
}

function StatusMark({ status }: { status: SourceDocument["status"] }) {
  if (status === "ready") return <Check size={14} className="ready-check" aria-label="Ready" />;
  if (status === "processing") return <span className="mini-spinner" aria-label="Processing" />;
  if (status === "failed") return <XCircle size={14} color="#d66a73" aria-label="Failed" />;
  return <span className="local-tag">{status === "sample" ? "Sample" : "Local"}</span>;
}

export function DocumentItem({ document, variant, selected = false, onSelect }: DocumentItemProps) {
  const isSidebar = variant === "sidebar";
  const content = (
    <>
      <span className={`${isSidebar ? "file-icon" : "source-file-icon"} ${document.kind}`}>
        {document.kind === "pdf" ? <FileText size={isSidebar ? 16 : 17} /> : <FileImage size={isSidebar ? 16 : 17} />}
      </span>
      <span className={isSidebar ? "document-info" : "source-text"}>
        {isSidebar ? (
          <>
            <span className="document-name">{document.name}</span>
            <span className="document-meta">{getStatusLabel(document.status, document.size)}</span>
          </>
        ) : (
          <>
            <strong>{document.name}</strong>
            <span>{document.size}</span>
            {(document.status === "sample" || document.status === "local") && (
              <span className="source-status-note">{document.status === "sample" ? "Sample only · not indexed" : "Local only · not uploaded"}</span>
            )}
          </>
        )}
      </span>
      <StatusMark status={document.status} />
    </>
  );

  if (isSidebar) {
    return (
      <button
        type="button"
        className={`document-row ${selected ? "selected" : ""}`}
        onClick={() => onSelect?.(document.id)}
        title={document.name}
        aria-pressed={selected}
      >
        {content}
      </button>
    );
  }

  return (
    <button type="button" className="source-item" onClick={() => onSelect?.(document.id)} title={document.name}>
      {content}
    </button>
  );
}
