import { ArrowRight, BookOpen, Plus, ShieldCheck, Sparkles } from "lucide-react";
import type { SourceDocument } from "@/types";
import { DocumentItem } from "@/components/documents/DocumentItem";
import { UploadDropzone } from "@/components/documents/UploadDropzone";

interface KnowledgeSourcesPanelProps {
  documents: SourceDocument[];
  activeDocumentId: string;
  readyCount: number;
  processingCount: number;
  onSelectDocument: (documentId: string) => void;
  onOpenFilePicker: () => void;
  onFilesAdded: (files: FileList | File[] | null) => void;
}

export function KnowledgeSourcesPanel({
  documents,
  activeDocumentId,
  readyCount,
  processingCount,
  onSelectDocument,
  onOpenFilePicker,
  onFilesAdded,
}: KnowledgeSourcesPanelProps) {
  const visibleDocuments = documents.slice(0, 5);
  const sampleCount = documents.filter((document) => document.status === "sample").length;
  const localCount = documents.filter((document) => document.status === "local").length;

  return (
    <aside className="right-panel">
      <div className="right-panel-heading">
        <div><span className="panel-icon"><BookOpen size={16} /></span><strong>Knowledge sources</strong></div>
        <button type="button" className="icon-button tiny" onClick={onOpenFilePicker} aria-label="Add source"><Plus size={16} /></button>
      </div>
      <p className="panel-description">Documents available to ground your answers.</p>
      <div className="source-summary">
        <span className="summary-dot" />
        <span>{readyCount} sources ready</span>
        <span className="summary-divider" />
        <span>{processingCount} processing</span>
        {(sampleCount > 0 || localCount > 0) && (
          <span className="demo-source-count">{sampleCount + localCount} demo</span>
        )}
      </div>
      <div className="source-list">
        {visibleDocuments.map((document) => (
          <DocumentItem
            key={document.id}
            document={document}
            variant="source"
            selected={activeDocumentId === document.id}
            onSelect={onSelectDocument}
          />
        ))}
      </div>
      <UploadDropzone onBrowse={onOpenFilePicker} onFilesAdded={onFilesAdded} />
      <div className="how-card">
        <div className="how-icon"><Sparkles size={15} /></div>
        <strong>Answers grounded in your files</strong>
        <p>The planned RAG pipeline will retrieve relevant passages and return page-level citations. It is not connected yet.</p>
        <div className="pipeline-mini"><span>Document</span><ArrowRight size={12} /><span>Retrieve</span><ArrowRight size={12} /><span>Answer</span></div>
      </div>
      <div className="right-panel-footer"><ShieldCheck size={14} /><span>Demo UI · backend not connected</span></div>
    </aside>
  );
}
