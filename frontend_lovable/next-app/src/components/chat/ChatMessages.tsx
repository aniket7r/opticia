"use client";

import { useRef, useEffect, useMemo, useState, useCallback } from "react";
import { Bot, ArrowDown, Check } from "lucide-react";
import { MessageBubble, type Message, MarkdownContent } from "./MessageBubble";
import { MessageActions } from "./MessageActions";
import { ThinkingDisplay } from "./ThinkingDisplay";
import type { ThinkingStepData } from "./ThinkingStep";

type ChatItem =
  | { kind: "message"; message: Message }
  | { kind: "thinking"; id: string; steps: ThinkingStepData[]; isComplete: boolean; defaultCollapsed?: boolean };


function AiHeader({ timestamp }: { timestamp?: Date }) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-foreground/10">
        <Bot className="h-3.5 w-3.5 text-foreground/70" />
      </div>
      <span className="text-[13px] font-semibold tracking-tight text-foreground">
        Opticia
      </span>
      {timestamp && (
        <span className="text-[11px] font-normal tracking-wide text-muted-foreground/60 opacity-0 group-hover/ai:opacity-100 transition-opacity duration-200">
          {timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      )}
    </div>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-16">
      <div className="flex items-center gap-2.5 mb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-foreground/10">
          <Bot className="h-4.5 w-4.5 text-foreground/70" />
        </div>
      </div>
      <h2 className="text-xl font-semibold tracking-tight text-foreground">
        {getGreeting()}
      </h2>
      <p className="mt-1 text-[13.5px] text-muted-foreground">
        How can I help you today?
      </p>
    </div>
  );
}

interface ChatMessagesProps {
  compact?: boolean;
  messages?: Message[];
  thinkingSteps?: ThinkingStepData[];
  isThinking?: boolean;
}

export function ChatMessages({ compact = false, messages = [], thinkingSteps = [], isThinking = false }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollDown, setShowScrollDown] = useState(false);

  const realMessages = useMemo(
    () => messages.filter((m) => m.role !== "system"),
    [messages]
  );

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [realMessages, scrollToBottom]);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const handleScroll = () => {
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      setShowScrollDown(distanceFromBottom > 100);
    };
    el.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  if (realMessages.length === 0) {
    return (
      <div className="flex h-full flex-col overflow-y-auto overscroll-contain pt-6 scroll-smooth scrollbar-hidden">
        <div className="w-full flex-1 flex flex-col">
          <EmptyState />
          <div ref={bottomRef} />
        </div>
      </div>
    );
  }

  // Insert thinking steps before the last AI message
  const items: ChatItem[] = [];
  const lastAiIndex = realMessages.reduce(
    (last: number, m, i) => (m.role === "ai" ? i : last), -1
  );

  realMessages.forEach((msg, i) => {
    if (thinkingSteps.length > 0 && i === lastAiIndex && !compact) {
      items.push({
        kind: "thinking",
        id: "thinking-live",
        steps: thinkingSteps,
        isComplete: !isThinking,
        defaultCollapsed: !isThinking,
      });
    }
    items.push({ kind: "message", message: msg });
  });


  const displayItems = compact ? items.slice(-2) : items;

  // Group consecutive non-user items under one AI header
  const result: Array<{ type: "user"; item: ChatItem } | { type: "ai-group"; items: ChatItem[] }> = [];

  for (const item of displayItems) {
    const isUser = item.kind === "message" && item.message.role === "user";
    if (isUser) {
      result.push({ type: "user", item });
    } else {
      const last = result[result.length - 1];
      if (last && last.type === "ai-group") {
        last.items.push(item);
      } else {
        result.push({ type: "ai-group", items: [item] });
      }
    }
  }

  return (
    <div className="relative h-full">
      <div ref={scrollContainerRef} className="flex h-full flex-col overflow-y-auto overscroll-contain pt-6 pb-[24px] scroll-smooth scrollbar-hidden">
        <div className="w-full">
          {compact ? (
            <div className="flex flex-1 items-end">
              <div className="w-full">
                {displayItems.map((item) =>
                  item.kind === "message" ? (
                    <MessageBubble key={item.message.id} message={item.message} />
                  ) : null
                )}
              </div>
            </div>
          ) : (
            result.map((group, gi) => {
              if (group.type === "user") {
                return <MessageBubble key={group.item.kind === "message" ? group.item.message.id : gi} message={(group.item as any).message} />;
              }
              return (
                <div key={`ai-group-${gi}`} className="group/ai py-3 animate-fade-in">
                  <AiHeader timestamp={
                    group.items.find((i) => i.kind === "message")?.kind === "message"
                      ? (group.items.find((i) => i.kind === "message") as any).message.timestamp
                      : undefined
                  } />
                  <div className="max-w-[85%]">
                    {group.items.map((item) =>
                      item.kind === "thinking" ? (
                        <ThinkingDisplay
                          key={item.id}
                          steps={item.steps}
                          isComplete={item.isComplete}
                          defaultCollapsed={item.defaultCollapsed}
                        />
                      ) : item.kind === "message" ? (
                        <div key={item.message.id}>
                          {item.message.type === "task-summary" && (
                            <span className="mb-1.5 flex items-center gap-1 text-xs font-medium text-success tracking-wide"><Check className="h-3.5 w-3.5" /> Task Complete</span>
                          )}
                          <MarkdownContent
                            content={item.message.content}
                            className="prose dark:prose-invert max-w-none text-base leading-[1.7] tracking-normal text-foreground [&_*]:text-foreground [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:mb-2 [&_ol]:mb-2 [&_pre]:bg-muted [&_pre]:rounded-lg [&_pre]:p-3 [&_code]:text-xs [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_h1]:text-lg [&_h2]:text-base [&_h3]:text-base [&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-medium"
                          />
                        </div>
                      ) : null
                    )}
                    <div className="mt-1.5">
                      <MessageActions
                        content={group.items
                          .filter((i) => i.kind === "message")
                          .map((i) => (i as any).message.content)
                          .join("\n")}
                        showVotes
                      />
                    </div>
                  </div>
                </div>
              );
            })
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Scroll to bottom button — pinned to bottom-right of the chat lane */}
      {showScrollDown && (
        <div className="absolute bottom-4 right-0 z-20">
          <button
            onClick={scrollToBottom}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-card shadow-md transition-all duration-200 hover:bg-accent active:scale-90"
            aria-label="Scroll to bottom"
          >
              <ArrowDown className="h-4 w-4 text-foreground" />
          </button>
        </div>
      )}
    </div>
  );
}
