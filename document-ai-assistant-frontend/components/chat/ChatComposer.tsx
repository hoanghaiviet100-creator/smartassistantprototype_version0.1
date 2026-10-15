"use client";

import { useState, type DragEvent, type KeyboardEvent } from "react";
import { ArrowUp, ChevronDown, Layers3, Paperclip, UploadCloud } from "lucide-react";
import type { SourceDocument } from "@/types";

interface ChatComposerProps {
  question: string;
  onQuestionChange: (value: string) => void;
  onSend: () => void;
  onOpenFilePicker: () => void;
  onFilesAdded: (files: FileList | File[] | null) => void;
  documents: SourceDocument[];
  activeDocumentId: string;
  onActiveDocumentChange: (documentId: string) => void;
}

export function ChatComposer({
  question,
  onQuestionChange,
  onSend,
  onOpenFilePicker,
  onFilesAdded,
  documents,
  activeDocumentId,
  onActiveDocumentChange,
}: ChatComposerProps) {
  const [isDragging, setIsDragging] = useState(false);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    onFilesAdded(event.dataTransfer.files);
  }

  return (
    <>
      <div
        className={`composer-wrap ${isDragging ? "dragging" : ""}`}
        onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        {isDragging && <div className="drop-overlay"><UploadCloud size={24} /><strong>Drop files to add them</strong></div>}
        <textarea
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything about your documents..."
          rows={2}
          aria-label="Ask a question"
        />
        <div className="composer-bottom">
          <div className="composer-tools">
            <button type="button" className="tool-button" onClick={onOpenFilePicker}><Paperclip size={15} /> Attach files</button>
            <span className="composer-divider" />
            <label className="scope-select-wrap">
              <Layers3 size={14} />
              <select
                className="scope-select"
                aria-label="Document search scope"
                value={activeDocumentId}
                onChange={(event) => onActiveDocumentChange(event.target.value)}
              >
                <option value="all">All documents</option>
                {documents.map((document) => (
                  <option key={document.id} value={document.id}>{document.name}</option>
                ))}
              </select>
              <ChevronDown size={13} />
            </label>
          </div>
          <button type="button" className="send-button" onClick={onSend} disabled={!question.trim()} aria-label="Send message"><ArrowUp size={17} /></button>
        </div>
      </div>
      <div className="composer-footnote"><span aria-hidden="true">ⓘ</span> Demo only: files are not uploaded or searched yet. <span>·</span> Enter to send, Shift + Enter for a new line.</div>
    </>
  );
}
