"use client";

import { cn } from "@/lib/utils";
import { Bot, Check } from "lucide-react";
import { Marked } from "marked";
import { useMemo } from "react";
import { MessageActions } from "./MessageActions";

const marked = new Marked({ async: false, breaks: true, gfm: true });

export interface Message {
  id: string;
  role: "user" | "ai" | "system";
  content: string;
  timestamp: Date;
  type?: "text" | "thinking" | "task-summary";
}

interface MessageBubbleProps {
  message: Message;
}

export function MarkdownContent({ content, className }: { content: string; className?: string }) {
  const html = useMemo(() => {
    return marked.parse(content) as string;
  }, [content]);

  return (
    <div
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === "system") {
    return (
      <div className="flex justify-center py-3">
        <span className="rounded-full bg-accent px-4 py-1.5 text-xs text-muted-foreground font-medium">
          {message.content}
        </span>
      </div>
    );
  }

  const isUser = message.role === "user";

  if (!isUser) {
    return (
      <div className="group/ai flex py-3 animate-fade-in">
        <div className="max-w-[85%]">
          <div className="flex items-center gap-2 mb-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-foreground/10">
              <Bot className="h-3.5 w-3.5 text-foreground/70" />
            </div>
            <span className="text-[13px] font-semibold tracking-tight text-foreground">
              gemini3
            </span>
            <span className="text-[11px] font-normal tracking-wide text-muted-foreground/60 opacity-0 group-hover/ai:opacity-100 transition-opacity duration-200">
              {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
          </div>
          {message.type === "task-summary" && (
            <span className="mb-1.5 flex items-center gap-1 text-xs font-medium text-success tracking-wide"><Check className="h-3.5 w-3.5" /> Task Complete</span>
          )}
          <MarkdownContent
            content={message.content}
            className="prose dark:prose-invert max-w-none text-base leading-[1.7] tracking-normal text-foreground [&_*]:text-foreground [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:mb-2 [&_ol]:mb-2 [&_pre]:bg-muted [&_pre]:rounded-lg [&_pre]:p-3 [&_code]:text-xs [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_h1]:text-lg [&_h2]:text-base [&_h3]:text-base [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-medium"
          />
          <div className="mt-1.5">
            <MessageActions content={message.content} showVotes />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="group/user flex py-1.5 animate-fade-in justify-end items-start gap-2">
      <span className="mt-3 shrink-0 text-[11px] font-normal tracking-wide text-muted-foreground/60 opacity-0 group-hover/user:opacity-100 transition-opacity duration-200">
        {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </span>
      <div className="max-w-[80%] rounded-2xl rounded-br-lg bg-muted px-4 py-3 text-base leading-[1.6] tracking-normal text-foreground">
        <MarkdownContent
          content={message.content}
          className="prose dark:prose-invert max-w-none text-base leading-[1.6] tracking-normal text-foreground [&_*]:text-foreground [&_p]:mb-1 [&_p:last-child]:mb-0 [&_pre]:bg-background/50 [&_pre]:rounded-lg [&_pre]:p-3 [&_code]:text-xs [&_code]:bg-background/50 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0"
        />
      </div>
      <div className="mt-auto mb-1">
        <MessageActions content={message.content} />
      </div>
    </div>
  );
}
