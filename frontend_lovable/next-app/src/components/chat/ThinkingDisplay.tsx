"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThinkingStep, type ThinkingStepData } from "./ThinkingStep";

export interface ThinkingDisplayProps {
  steps: ThinkingStepData[];
  isComplete: boolean;
  defaultCollapsed?: boolean;
}

export function ThinkingDisplay({ steps, isComplete, defaultCollapsed = false }: ThinkingDisplayProps) {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const completedCount = steps.filter((s) => s.status === "complete").length;

  if (isCollapsed) {
    return (
      <div className="flex justify-start py-1.5">
        <button
          onClick={() => setIsCollapsed(false)}
          className="group flex items-center gap-2.5 rounded-xl border border-border/60 bg-card px-4 py-2.5 text-sm text-muted-foreground transition-all duration-200 hover:bg-accent/50 hover:border-border hover:shadow-sm"
          aria-expanded={false}
          aria-label="Expand thinking steps"
        >
          {isComplete ? (
            <Sparkles className="h-3.5 w-3.5 text-foreground/40" />
          ) : (
            <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
          )}
          <span className="font-medium text-[13px]">
            {isComplete
              ? `Completed ${completedCount} steps`
              : `Working · ${completedCount} of ${steps.length}`}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground/40 transition-transform duration-200 group-hover:translate-y-0.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex justify-start py-1.5">
      <div className="max-w-[80%] rounded-xl border border-border/60 bg-card animate-fade-in overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setIsCollapsed(true)}
          className="flex w-full items-center gap-2.5 px-4 py-3 text-[13px] font-medium text-muted-foreground hover:bg-accent/30 transition-colors duration-200 border-b border-border/40"
          aria-expanded={true}
          aria-label="Collapse thinking steps"
        >
          {isComplete ? (
            <Sparkles className="h-3.5 w-3.5 text-foreground/40" />
          ) : (
            <Loader2 className="h-3.5 w-3.5 text-primary animate-spin" />
          )}
          <span className="flex-1 text-left">
            {isComplete ? "Thought process" : "Working on it…"}
          </span>
          <span className="text-[11px] text-muted-foreground/40 mr-1">
            {completedCount}/{steps.length}
          </span>
          <ChevronUp className="h-3.5 w-3.5 text-muted-foreground/40" />
        </button>

        {/* Steps timeline */}
        <div className="px-4 pt-3 pb-2">
          {steps.map((step, i) => (
            <ThinkingStep key={i} step={step} index={i} isLast={i === steps.length - 1} />
          ))}
        </div>
      </div>
    </div>
  );
}
