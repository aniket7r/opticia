"use client";

import { cn } from "@/lib/utils";
import type { ChatSummary } from "./types";

interface ChatCardProps {
  chat: ChatSummary;
  isActive: boolean;
  onClick: () => void;
}

export function ChatCard({ chat, isActive, onClick }: ChatCardProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left px-3 py-2 rounded-lg transition-colors text-[13.5px] truncate",
        isActive
          ? "bg-accent text-foreground font-medium"
          : "text-foreground/80 hover:bg-accent/50"
      )}
      aria-label={`Open chat: ${chat.title}`}
      aria-current={isActive ? "true" : undefined}
    >
      <span className="truncate">{chat.title}</span>
    </button>
  );
}
