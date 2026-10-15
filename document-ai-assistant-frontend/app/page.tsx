"use client";

import { useRef, useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { MessageList } from "@/components/chat/MessageList";
import { SuggestedQuestions } from "@/components/chat/SuggestedQuestions";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { KnowledgeSourcesPanel } from "@/components/sources/KnowledgeSourcesPanel";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";

export default function Home() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [activeDocumentId, setActiveDocumentId] = useState("all");
  const [showSuggestions, setShowSuggestions] = useState(true);
  const documentState = useDocuments();
  const chat = useChat({ onNotice: documentState.setNotice });

  function openFilePicker() {
    fileInput.current?.click();
  }

  function sendMessage() {
    chat.sendMessage(activeDocumentId);
    setShowSuggestions(false);
  }

  return (
    <main className="app-shell">
      <Sidebar
        documents={documentState.documents}
        visibleDocuments={documentState.visibleDocuments}
        activeDocumentId={activeDocumentId}
        search={documentState.search}
        onSearchChange={documentState.setSearch}
        onSelectDocument={setActiveDocumentId}
        onOpenFilePicker={openFilePicker}
        onNewConversation={() => {
          chat.startNewConversation();
          setShowSuggestions(true);
        }}
      />

      <section className="main-panel">
        <Topbar />

        <div className="chat-layout">
          <div className="chat-column">
            <div className="conversation-header">
              <div>
                <div className="eyebrow"><span className="eyebrow-dot" /> DOCUMENT INTELLIGENCE</div>
                <h1>Make sense of your <span>documents.</span></h1>
                <p>Ask questions. Find answers. Keep every source in reach.</p>
              </div>
              <div className="header-art" aria-hidden="true">
                <div className="art-sheet sheet-back" />
                <div className="art-sheet sheet-front"><span /><span /><span /><i /></div>
                <div className="art-spark"><Sparkles size={20} /></div>
              </div>
            </div>

            {showSuggestions ? (
              <SuggestedQuestions onChoose={chat.setQuestion} />
            ) : (
              <button
                type="button"
                className="suggestions-reopen"
                onClick={() => setShowSuggestions(true)}
              >
                <Sparkles size={14} /> Suggested questions <ArrowRight size={13} />
              </button>
            )}

            <MessageList messages={chat.messages} />

            <ChatComposer
              question={chat.question}
              onQuestionChange={chat.setQuestion}
              onSend={sendMessage}
              onOpenFilePicker={openFilePicker}
              onFilesAdded={documentState.addFiles}
              documents={documentState.documents}
              activeDocumentId={activeDocumentId}
              onActiveDocumentChange={setActiveDocumentId}
            />
          </div>

          <KnowledgeSourcesPanel
            documents={documentState.documents}
            activeDocumentId={activeDocumentId}
            readyCount={documentState.readyCount}
            processingCount={documentState.processingCount}
            onSelectDocument={setActiveDocumentId}
            onOpenFilePicker={openFilePicker}
            onFilesAdded={documentState.addFiles}
          />
        </div>

        <div className="status-toast" role="status"><span className="toast-dot" />{documentState.notice}</div>
      </section>

      <input
        ref={fileInput}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
        multiple
        hidden
        onChange={(event) => {
          documentState.addFiles(event.currentTarget.files);
          event.currentTarget.value = "";
        }}
      />
    </main>
  );
}
