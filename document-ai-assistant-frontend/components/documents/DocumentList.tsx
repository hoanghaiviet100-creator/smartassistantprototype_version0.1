import type { SourceDocument } from "@/types";
import { DocumentItem } from "@/components/documents/DocumentItem";

interface DocumentListProps {
  documents: SourceDocument[];
  activeDocumentId: string;
  onSelectDocument: (documentId: string) => void;
}

export function DocumentList({ documents, activeDocumentId, onSelectDocument }: DocumentListProps) {
  if (documents.length === 0) {
    return <p className="empty-search">No matching files.</p>;
  }

  return (
    <div className="document-list">
      {documents.map((document) => (
        <DocumentItem
          key={document.id}
          document={document}
          variant="sidebar"
          selected={activeDocumentId === document.id}
          onSelect={onSelectDocument}
        />
      ))}
    </div>
  );
}
