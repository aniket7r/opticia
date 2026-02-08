"use client";

import { useState } from "react";
import { Copy, ThumbsUp, ThumbsDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface MessageActionsProps {
  content: string;
  showVotes?: boolean;
}

export function MessageActions({ content, showVotes = false }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [vote, setVote] = useState<"up" | "down" | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success("Copied to clipboard");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Failed to copy");
    }
  };

  const handleVote = (type: "up" | "down") => {
    if (vote === type) {
      setVote(null);
    } else {
      setVote(type);
      toast.success(type === "up" ? "Thanks for the feedback!" : "We'll try to improve");
    }
  };

  return (
    <div className="flex items-center gap-0.5 opacity-0 group-hover/ai:opacity-100 group-hover/user:opacity-100 transition-opacity duration-200">
      <button
        onClick={handleCopy}
        className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground/60 hover:text-foreground hover:bg-accent transition-colors"
        aria-label="Copy message"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
      {showVotes && (
        <>
          <button
            onClick={() => handleVote("up")}
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-md transition-colors",
              vote === "up"
                ? "text-green-500 bg-green-500/10"
                : "text-muted-foreground/60 hover:text-foreground hover:bg-accent"
            )}
            aria-label="Upvote"
          >
            <ThumbsUp className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => handleVote("down")}
            className={cn(
              "flex h-7 w-7 items-center justify-center rounded-md transition-colors",
              vote === "down"
                ? "text-red-500 bg-red-500/10"
                : "text-muted-foreground/60 hover:text-foreground hover:bg-accent"
            )}
            aria-label="Downvote"
          >
            <ThumbsDown className="h-3.5 w-3.5" />
          </button>
        </>
      )}
    </div>
  );
}
