"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic } from "lucide-react";
import { cn } from "@/lib/utils";

interface TextInputProps {
  onSend?: (text: string) => void;
  onStartRecording?: () => void;
}

export function TextInput({ onSend, onStartRecording }: TextInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [text]);

  const handleSend = () => {
    if (!text.trim()) return;
    onSend?.(text.trim());
    setText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasText = text.trim().length > 0;

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message..."
        rows={1}
        className={cn(
          "flex-1 resize-none rounded-2xl bg-surface-elevated px-4 py-2.5 text-sm text-foreground",
          "placeholder:text-muted-foreground",
          "border border-border focus:border-primary focus:outline-none transition-default",
          "max-h-[120px]"
        )}
        aria-label="Message input"
      />
      <button
        onClick={hasText ? handleSend : onStartRecording}
        className={cn(
          "tap-target flex shrink-0 items-center justify-center rounded-full p-3 transition-default",
          hasText
            ? "bg-primary text-primary-foreground hover:bg-primary/90"
            : "bg-surface-elevated text-muted-foreground hover:text-foreground hover:bg-muted"
        )}
        aria-label={hasText ? "Send message" : "Start voice recording"}
      >
        {hasText ? <Send className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
      </button>
    </div>
  );
}
