"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { Search, X, SquarePen } from "lucide-react";
import { cn } from "@/lib/utils";
import { format } from "date-fns";
import type { ChatSummary } from "./types";

interface SearchOverlayProps {
  isOpen: boolean;
  onClose: () => void;
  chats: ChatSummary[];
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
}

export function SearchOverlay({
  isOpen,
  onClose,
  chats,
  onSelectChat,
  onNewChat,
}: SearchOverlayProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  const filtered = useMemo(() => {
    if (!query.trim()) return chats;
    const q = query.toLowerCase();
    return chats.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        (c.lastMessage && c.lastMessage.toLowerCase().includes(q))
    );
  }, [chats, query]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-[60] backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Search panel */}
      <div className="fixed inset-x-0 top-0 z-[70] flex justify-center pt-[10vh]">
        <div className="w-full max-w-[600px] mx-4 rounded-2xl border border-border bg-card shadow-2xl overflow-hidden animate-in fade-in-0 zoom-in-95 duration-200">
          {/* Search input */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-border">
            <Search className="h-5 w-5 text-muted-foreground shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search tasks..."
              className="flex-1 bg-transparent text-lg text-foreground placeholder:text-muted-foreground/50 focus:outline-none"
            />
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              aria-label="Close search"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Results */}
          <div className="max-h-[60vh] overflow-y-auto">
            {/* New task */}
            <button
              onClick={() => {
                onNewChat();
                onClose();
              }}
              className="flex items-center gap-3 w-full px-5 py-3.5 text-foreground hover:bg-accent transition-colors text-sm"
            >
              <div className="flex items-center justify-center h-9 w-9 rounded-full bg-muted shrink-0">
                <SquarePen className="h-4 w-4 text-muted-foreground" />
              </div>
              <span className="font-medium">New task</span>
            </button>

            {/* Chat results */}
            {filtered.length > 0 ? (
              filtered.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => {
                    onSelectChat(chat.id);
                    onClose();
                  }}
                  className="flex items-center gap-3 w-full px-5 py-3.5 text-left hover:bg-accent transition-colors group"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-foreground truncate">
                        {chat.title}
                      </span>
                      <span className="text-[11px] text-muted-foreground shrink-0">
                        {format(chat.createdAt, "M/d")}
                      </span>
                    </div>
                    {chat.lastMessage && (
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {chat.lastMessage}
                      </p>
                    )}
                  </div>
                </button>
              ))
            ) : (
              <div className="px-5 py-8 text-center text-sm text-muted-foreground">
                No tasks found for "{query}"
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
