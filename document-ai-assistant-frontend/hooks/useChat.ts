"use client";

import { useState } from "react";
import type { ChatMessage } from "@/types";

const welcomeMessage: ChatMessage = {
  id: "welcome",
  role: "assistant",
  origin: "welcome",
  content:
    "Hi! I’m your document assistant. Ask me a question about your files, and I’ll help you find the relevant information with sources.",
};

interface UseChatOptions {
  onNotice: (message: string) => void;
}

export function useChat({ onNotice }: UseChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [question, setQuestion] = useState("");

  function startNewConversation() {
    setMessages([welcomeMessage]);
    setQuestion("");
    onNotice("New conversation started. Demo mode is still active.");
  }

  function sendMessage(selectedDocumentId: string) {
    const trimmed = question.trim();
    if (!trimmed) return;

    const now = Date.now();
    const userMessage: ChatMessage = {
      id: `user-${now}`,
      role: "user",
      content: trimmed,
    };

    // Deliberately no fabricated answer or citation while the RAG API is unavailable.
    const mockMessage: ChatMessage = {
      id: `assistant-${now + 1}`,
      role: "assistant",
      origin: "mock",
      content:
        "Demo mode: your question was captured, but no answer was generated. Connect the FastAPI RAG backend to retrieve relevant passages and return verifiable citations.",
    };

    setMessages((current) => [...current, userMessage, mockMessage]);
    setQuestion("");
    onNotice(
      selectedDocumentId === "all"
        ? "Demo response only · No documents were searched and no LLM call was made."
        : "Demo response only · The selected file is local/sample data and has not been indexed.",
    );
  }

  return {
    messages,
    question,
    setQuestion,
    sendMessage,
    startNewConversation,
  };
}
