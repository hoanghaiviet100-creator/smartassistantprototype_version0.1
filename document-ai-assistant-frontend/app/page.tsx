"use client";

import { ChangeEvent, KeyboardEvent, useRef, useState } from "react";
import {
  ArrowDown, ArrowRight, ArrowUp, BookOpen, Check, ChevronDown,
  CircleHelp, FileImage, FileText, FolderOpen, Globe2, Layers3,
  MessageSquareText, MoreHorizontal, Paperclip, Plus, Search, ShieldCheck,
  Sparkles, UploadCloud, X
} from "lucide-react";

type SourceDocument = {
  id: string;
  name: string;
  size: string;
  kind: "pdf" | "image";
  status: "ready" | "processing";
};

type Citation = { document: string; page: number; excerpt: string };
type Message = {
  id: string;
  role: "assistant" | "user";
  content: string;
  citations?: Citation[];
};

const starterDocs: SourceDocument[] = [
  { id: "sample-1", name: "Student handbook.pdf", size: "2.4 MB", kind: "pdf", status: "ready" },
  { id: "sample-2", name: "Research notes.pdf", size: "840 KB", kind: "pdf", status: "ready" },
];

const welcomeMessage: Message = {
  id: "welcome",
  role: "assistant",
  content: "Hi! I’m your document assistant. Ask me a question about your files, and I’ll help you find the relevant information with sources.",
};

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const [documents, setDocuments] = useState<SourceDocument[]>(starterDocs);
  const [messages, setMessages] = useState<Message[]>([welcomeMessage]);
  const [question, setQuestion] = useState("");
  const [activeDoc, setActiveDoc] = useState("all");
  const [search, setSearch] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [notice, setNotice] = useState("Demo mode · Answers are simulated until the RAG backend is connected.");
  const fileInput = useRef<HTMLInputElement>(null);

  const visibleDocs = documents.filter((doc) =>
    doc.name.toLowerCase().includes(search.toLowerCase())
  );

  function addFiles(fileList: FileList | null) {
    if (!fileList) return;
    const accepted = Array.from(fileList).filter((file) =>
      file.type === "application/pdf" ||
      file.type === "image/png" ||
      file.type === "image/jpeg" ||
      /\.(pdf|png|jpe?g)$/i.test(file.name)
    );

    if (accepted.length === 0) {
      setNotice("Unsupported file. Please choose a PDF, PNG, or JPG image.");
      return;
    }

    const additions: SourceDocument[] = accepted.map((file) => ({
      id: `${file.name}-${file.lastModified}-${Math.random().toString(36).slice(2, 7)}`,
      name: file.name,
      size: formatSize(file.size),
      kind: file.type === "application/pdf" || /\.pdf$/i.test(file.name) ? "pdf" : "image",
      status: "processing",
    }));

    setDocuments((current) => [...additions, ...current]);
    setNotice(`${accepted.length} file(s) added to the UI demo. Backend upload is not connected yet.`);

    // UI-only prototype: this simulates processing status, not OCR or indexing.
    window.setTimeout(() => {
      setDocuments((current) => current.map((doc) =>
        additions.some((added) => added.id === doc.id) ? { ...doc, status: "ready" } : doc
      ));
    }, 900);
  }

  function sendMessage() {
    const trimmed = question.trim();
    if (!trimmed) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };

    const assistantMessage: Message = {
      id: `assistant-${Date.now() + 1}`,
      role: "assistant",
      content: "This is a placeholder response. Once the FastAPI RAG backend is connected, this area will show an answer grounded in retrieved document chunks—not a hard-coded demo answer.",
      citations: [
        {
          document: activeDoc === "all"
            ? (documents.find((doc) => doc.status === "ready")?.name ?? "No document selected")
            : (documents.find((doc) => doc.id === activeDoc)?.name ?? "Selected document"),
          page: 1,
          excerpt: "Citation preview — real excerpts and page numbers will come from the retrieval API.",
        },
      ],
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setQuestion("");
    setNotice("Demo response shown. No LLM or RAG retrieval has run.");
  }

  function handleComposerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    addFiles(event.dataTransfer.files);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Layers3 size={19} strokeWidth={2.3} /></div>
          <span>documind<span className="brand-dot">.</span></span>
          <button className="icon-button sidebar-toggle" aria-label="Collapse sidebar"><ArrowDown size={16} /></button>
        </div>

        <button className="new-chat" onClick={() => setMessages([welcomeMessage])}>
          <Plus size={17} /> New conversation <span className="shortcut">⌘ K</span>
        </button>

        <div className="nav-label">WORKSPACE</div>
        <button className="nav-item active"><MessageSquareText size={17} /> Ask documents</button>
        <button className="nav-item" onClick={() => fileInput.current?.click()}><FolderOpen size={17} /> My documents <span className="nav-count">{documents.length}</span></button>

        <div className="documents-heading">
          <span className="nav-label">YOUR LIBRARY</span>
          <button className="icon-button tiny" onClick={() => fileInput.current?.click()} aria-label="Upload document"><Plus size={16} /></button>
        </div>
        <div className="search-box">
          <Search size={14} />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search files..." aria-label="Search files" />
        </div>

        <div className="document-list">
          {visibleDocs.map((doc) => (
            <button
              key={doc.id}
              className={`document-row ${activeDoc === doc.id ? "selected" : ""}`}
              onClick={() => setActiveDoc(doc.id)}
              title={doc.name}
            >
              <span className={`file-icon ${doc.kind}`}>
                {doc.kind === "pdf" ? <FileText size={16} /> : <FileImage size={16} />}
              </span>
              <span className="document-info">
                <span className="document-name">{doc.name}</span>
                <span className="document-meta">{doc.size} · {doc.status === "ready" ? "Ready" : "Processing"}</span>
              </span>
              {doc.status === "ready" ? <Check size={14} className="ready-check" /> : <span className="mini-spinner" />}
            </button>
          ))}
          {visibleDocs.length === 0 && <p className="empty-search">No matching files.</p>}
        </div>

        <div className="sidebar-spacer" />
        <div className="plan-card">
          <div className="plan-icon"><Sparkles size={16} /></div>
          <div>
            <strong>Prototype workspace</strong>
            <p>Local UI · Backend coming next</p>
          </div>
        </div>
        <button className="profile-row">
          <div className="avatar">V</div>
          <div className="profile-info"><strong>Workspace</strong><span>Personal project</span></div>
          <MoreHorizontal size={18} className="muted-icon" />
        </button>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="breadcrumb"><span>Workspace</span><span className="slash">/</span><strong>Ask documents</strong><ChevronDown size={14} /></div>
          <div className="topbar-actions">
            <span className="privacy-note"><ShieldCheck size={14} /> Private workspace</span>
            <button className="help-button" aria-label="Help"><CircleHelp size={17} /></button>
          </div>
        </header>

        <div className="chat-layout">
          <div className="chat-column">
            <div className="conversation-header">
              <div>
                <div className="eyebrow"><span className="eyebrow-dot" /> DOCUMENT INTELLIGENCE</div>
                <h1>Make sense of your <span>documents.</span></h1>
                <p>Ask questions. Find answers. Keep every source in reach.</p>
              </div>
              <div className="header-art"><div className="art-sheet sheet-back" /><div className="art-sheet sheet-front"><span /><span /><span /><i /></div><div className="art-spark"><Sparkles size={20} /></div></div>
            </div>

            {messages.length === 1 && (
              <div className="suggestion-section">
                <div className="section-kicker">GET STARTED</div>
                <div className="suggestion-grid">
                  <button className="suggestion-card" onClick={() => setQuestion("Summarize the key points in my documents.")}>
                    <span className="suggestion-icon lavender"><BookOpen size={17} /></span>
                    <strong>Summarize a document</strong>
                    <span>Get the key ideas in seconds.</span>
                    <ArrowRight size={15} className="suggestion-arrow" />
                  </button>
                  <button className="suggestion-card" onClick={() => setQuestion("What are the most important dates and deadlines?")}>
                    <span className="suggestion-icon mint"><Search size={17} /></span>
                    <strong>Find key details</strong>
                    <span>Locate dates, facts, and figures.</span>
                    <ArrowRight size={15} className="suggestion-arrow" />
                  </button>
                  <button className="suggestion-card" onClick={() => setQuestion("Compare the main ideas across my documents.")}>
                    <span className="suggestion-icon peach"><Globe2 size={17} /></span>
                    <strong>Compare documents</strong>
                    <span>Connect information across files.</span>
                    <ArrowRight size={15} className="suggestion-arrow" />
                  </button>
                </div>
              </div>
            )}

            <div className="messages" aria-live="polite">
              {messages.map((message) => (
                <article className={`message ${message.role}`} key={message.id}>
                  {message.role === "assistant" ? (
                    <div className="assistant-avatar"><Sparkles size={16} /></div>
                  ) : (
                    <div className="user-avatar">Y</div>
                  )}
                  <div className="message-body">
                    <div className="message-author">{message.role === "assistant" ? "DocuMind" : "You"} <span>{message.role === "assistant" ? "· AI assistant" : "· Just now"}</span></div>
                    <p>{message.content}</p>
                    {message.citations?.map((citation, index) => (
                      <div className="citation-card" key={`${citation.document}-${index}`}>
                        <div className="citation-top"><FileText size={15} /><strong>{citation.document}</strong><span>Page {citation.page}</span></div>
                        <p>“{citation.excerpt}”</p>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>

            <div className={`composer-wrap ${isDragging ? "dragging" : ""}`} onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }} onDragLeave={() => setIsDragging(false)} onDrop={handleDrop}>
              {isDragging && <div className="drop-overlay"><UploadCloud size={24} /><strong>Drop files to add them</strong></div>}
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleComposerKey}
                placeholder="Ask anything about your documents..."
                rows={2}
                aria-label="Ask a question"
              />
              <div className="composer-bottom">
                <div className="composer-tools">
                  <button className="tool-button" onClick={() => fileInput.current?.click()}><Paperclip size={15} /> Attach files</button>
                  <span className="composer-divider" />
                  <button className="scope-button" onClick={() => setActiveDoc(activeDoc === "all" ? (documents[0]?.id ?? "all") : "all")}>
                    <Layers3 size={14} /> {activeDoc === "all" ? "All documents" : "Selected document"} <ChevronDown size={13} />
                  </button>
                </div>
                <button className="send-button" onClick={sendMessage} disabled={!question.trim()} aria-label="Send message"><ArrowUp size={17} /></button>
              </div>
            </div>
            <div className="composer-footnote"><ShieldCheck size={12} /> Your documents stay in your workspace. <span>·</span> Enter to send, Shift + Enter for a new line.</div>
          </div>

          <aside className="right-panel">
            <div className="right-panel-heading"><div><span className="panel-icon"><BookOpen size={16} /></span><strong>Knowledge sources</strong></div><button className="icon-button tiny" onClick={() => fileInput.current?.click()} aria-label="Add source"><Plus size={16} /></button></div>
            <p className="panel-description">Documents available to ground your answers.</p>
            <div className="source-summary"><span className="summary-dot" /><span>{documents.filter((doc) => doc.status === "ready").length} sources ready</span><span className="summary-divider" /><span>{documents.filter((doc) => doc.status === "processing").length} processing</span></div>
            <div className="source-list">
              {documents.slice(0, 5).map((doc) => (
                <button className="source-item" key={doc.id} onClick={() => setActiveDoc(doc.id)}>
                  <span className={`source-file-icon ${doc.kind}`}>{doc.kind === "pdf" ? <FileText size={17} /> : <FileImage size={17} />}</span>
                  <span className="source-text"><strong>{doc.name}</strong><span>{doc.size}</span></span>
                  {doc.status === "ready" ? <Check size={14} className="ready-check" /> : <span className="mini-spinner" />}
                </button>
              ))}
            </div>
            <div className="upload-zone" onClick={() => fileInput.current?.click()} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") fileInput.current?.click(); }}>
              <div className="upload-icon"><UploadCloud size={19} /></div>
              <strong>Drop files or browse</strong>
              <span>PDF, PNG, JPG up to 20 MB</span>
              <span className="upload-link">Choose files <ArrowRight size={13} /></span>
            </div>
            <div className="how-card">
              <div className="how-icon"><Sparkles size={15} /></div>
              <strong>Answers grounded in your files</strong>
              <p>The RAG pipeline will retrieve relevant passages and attach page-level citations to each answer.</p>
              <div className="pipeline-mini"><span>Document</span><ArrowRight size={12} /><span>Retrieve</span><ArrowRight size={12} /><span>Answer</span></div>
            </div>
            <div className="right-panel-footer"><ShieldCheck size={14} /><span>Designed for source-backed answers</span></div>
          </aside>
        </div>
        <div className="status-toast" role="status"><span className="toast-dot" />{notice}</div>
      </section>

      <input
        ref={fileInput}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
        multiple
        hidden
        onChange={(event: ChangeEvent<HTMLInputElement>) => {
          addFiles(event.target.files);
          event.target.value = "";
        }}
      />
    </main>
  );
}
