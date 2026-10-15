import type { ChatMessage } from "@/types";
import { MessageBubble } from "@/components/chat/MessageBubble";

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  return (
    <div className="messages" aria-live="polite" aria-label="Conversation messages">
      {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
    </div>
  );
}
