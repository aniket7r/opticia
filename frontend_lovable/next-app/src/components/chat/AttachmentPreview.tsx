"use client";

import { X, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Attachment {
  id: string;
  name: string;
  type: "image" | "file";
  /** Data URL for images, or undefined for generic files */
  preview?: string;
}

interface AttachmentPreviewProps {
  attachments: Attachment[];
  onRemove: (id: string) => void;
}

export function AttachmentPreview({ attachments, onRemove }: AttachmentPreviewProps) {
  if (attachments.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4 pt-3 pb-1">
      {attachments.map((a) => (
        <div
          key={a.id}
          className={cn(
            "group relative flex items-center gap-2 rounded-xl border border-border bg-accent/50 transition-all duration-200",
            a.type === "image" ? "p-1" : "px-3 py-2"
          )}
        >
          {a.type === "image" && a.preview ? (
            <img
              src={a.preview}
              alt={a.name}
              className="h-16 w-16 rounded-lg object-cover"
            />
          ) : (
            <>
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="max-w-[120px] truncate text-xs text-foreground">
                {a.name}
              </span>
            </>
          )}
          <button
            onClick={() => onRemove(a.id)}
            className={cn(
              "absolute -right-1.5 -top-1.5 flex h-5 w-5 items-center justify-center rounded-full",
              "bg-foreground text-background shadow-sm",
              "opacity-0 transition-opacity duration-150 group-hover:opacity-100"
            )}
            aria-label={`Remove ${a.name}`}
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      ))}
    </div>
  );
}
