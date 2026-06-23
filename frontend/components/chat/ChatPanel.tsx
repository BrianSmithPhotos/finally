"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import type { ChatMessage } from "@/lib/types";
import { ChatMessageItem } from "./ChatMessageItem";

interface ChatPanelProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSend: (message: string) => void;
}

export function ChatPanel({ messages, isLoading, onSend }: ChatPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setInput("");
  };

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={() => setCollapsed(false)}
        className="flex h-full w-10 items-center justify-center rounded border border-border-muted bg-background-panel text-gray-400 hover:text-accent-yellow"
        aria-label="Expand chat panel"
        data-testid="chat-expand"
      >
        <span className="-rotate-90 whitespace-nowrap text-xs uppercase tracking-wide">Chat</span>
      </button>
    );
  }

  return (
    <section
      className="flex h-full w-80 flex-col rounded border border-border-muted bg-background-panel"
      data-testid="chat-panel"
    >
      <div className="flex items-center justify-between border-b border-border-muted px-3 py-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">AI Assistant</h2>
        <button
          type="button"
          onClick={() => setCollapsed(true)}
          aria-label="Collapse chat panel"
          data-testid="chat-collapse"
          className="text-gray-500 hover:text-accent-yellow"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3" data-testid="chat-messages">
        {messages.length === 0 && (
          <p className="text-sm text-gray-500">
            Ask FinAlly about your portfolio, request analysis, or have it execute trades.
          </p>
        )}
        {messages.map((message) => (
          <ChatMessageItem key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="mb-3 flex items-center gap-2 text-sm text-gray-500" data-testid="chat-loading">
            <span className="h-2 w-2 animate-pulse rounded-full bg-accent-yellow" />
            FinAlly is thinking...
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-border-muted p-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask FinAlly..."
          aria-label="Chat message"
          disabled={isLoading}
          className="flex-1 rounded border border-border-muted bg-background px-2 py-1 text-sm outline-none focus:border-accent-blue disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded bg-accent-purple px-3 py-1 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </section>
  );
}
