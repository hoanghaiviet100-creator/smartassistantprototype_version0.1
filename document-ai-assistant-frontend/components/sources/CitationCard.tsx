import { FileText } from "lucide-react";
import type { Citation } from "@/types";

export function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="citation-card">
      <div className="citation-top">
        <FileText size={15} />
        <strong>{citation.filename}</strong>
        {typeof citation.pageNumber === "number" && <span>Page {citation.pageNumber}</span>}
      </div>
      <p>“{citation.excerpt}”</p>
    </div>
  );
}
