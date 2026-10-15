import { Sparkles } from "lucide-react";
import type { ChatMessage } from "@/types";
import { CitationCard } from "@/components/sources/CitationCard";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isAssistant = message.role === "assistant";

  return (
    <article className={`message ${message.role}`}>
      {isAssistant ? (
        <div className="assistant-avatar"><Sparkles size={16} /></div>
      ) : (
        <div className="user-avatar">Y</div>
      )}
      <div className="message-body">
        <div className="message-author">
          {isAssistant ? "DocuMind" : "You"}
          <span>
            {message.origin === "mock"
              ? " · Demo mode (no AI call)"
              : isAssistant
                ? " · AI assistant"
                : " · Just now"}
          </span>
        </div>
        <p>{message.content}</p>
        {message.citations?.map((citation, index) => (
          <CitationCard key={`${citation.documentId}-${citation.chunkId ?? index}`} citation={citation} />
        ))}
      </div>
    </article>
  );
}
