import {
  ArrowDown, FolderOpen, Layers3, MessageSquareText, MoreHorizontal,
  Plus, Search, Sparkles,
} from "lucide-react";
import type { SourceDocument } from "@/types";
import { DocumentList } from "@/components/documents/DocumentList";

interface SidebarProps {
  documents: SourceDocument[];
  visibleDocuments: SourceDocument[];
  activeDocumentId: string;
  search: string;
  onSearchChange: (value: string) => void;
  onSelectDocument: (documentId: string) => void;
  onOpenFilePicker: () => void;
  onNewConversation: () => void;
}

export function Sidebar({
  documents,
  visibleDocuments,
  activeDocumentId,
  search,
  onSearchChange,
  onSelectDocument,
  onOpenFilePicker,
  onNewConversation,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"><Layers3 size={19} strokeWidth={2.3} /></div>
        <span>documind<span className="brand-dot">.</span></span>
        <button type="button" className="icon-button sidebar-toggle" aria-label="Collapse sidebar"><ArrowDown size={16} /></button>
      </div>

      <button type="button" className="new-chat" onClick={onNewConversation}>
        <Plus size={17} /> New conversation <span className="shortcut">⌘ K</span>
      </button>

      <div className="nav-label">WORKSPACE</div>
      <button type="button" className="nav-item active"><MessageSquareText size={17} /> Ask documents</button>
      <button type="button" className="nav-item" onClick={onOpenFilePicker}>
        <FolderOpen size={17} /> My documents <span className="nav-count">{documents.length}</span>
      </button>

      <div className="documents-heading">
        <span className="nav-label">YOUR LIBRARY</span>
        <button type="button" className="icon-button tiny" onClick={onOpenFilePicker} aria-label="Upload document"><Plus size={16} /></button>
      </div>
      <div className="search-box">
        <Search size={14} />
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search files..."
          aria-label="Search files"
        />
      </div>
      <DocumentList
        documents={visibleDocuments}
        activeDocumentId={activeDocumentId}
        onSelectDocument={onSelectDocument}
      />

      <div className="sidebar-spacer" />
      <div className="plan-card">
        <div className="plan-icon"><Sparkles size={16} /></div>
        <div>
          <strong>Prototype workspace</strong>
          <p>Local UI · Backend coming next</p>
        </div>
      </div>
      <button type="button" className="profile-row">
        <div className="avatar">V</div>
        <div className="profile-info"><strong>Workspace</strong><span>Personal project</span></div>
        <MoreHorizontal size={18} className="muted-icon" />
      </button>
    </aside>
  );
}
