"use client";

import { useState } from "react";
import { Check, ChevronDown, ChevronUp, X } from "lucide-react";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";
import type { Step } from "./types";

interface TaskProgressCardProps {
  steps: Step[];
  title?: string;
  onToggleStep?: (stepId: string) => void;
  onDismiss?: () => void;
}

function StepRow({ step, onToggle }: { step: Step; onToggle?: () => void }) {
  const [open, setOpen] = useState(false);
  const done = step.status === "completed";
  const isCurrent = step.status === "current";
  const upcoming = step.status === "upcoming";
  const hasContent = !!(step.description || step.warning);

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div
        className={cn(
          "flex w-full items-center gap-3 px-4 py-3.5 rounded-lg transition-all duration-200",
          isCurrent && "bg-blue-500/5 border-l-2 border-blue-500",
          done && "opacity-60",
          upcoming && "opacity-40"
        )}
      >
        {/* Clickable check / empty circle for toggling */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggle?.();
          }}
          className="shrink-0 flex items-center justify-center"
          aria-label={done ? "Mark as not done" : "Mark as done"}
        >
          {done ? (
            <Check className="h-5 w-5 text-emerald-500" strokeWidth={2.5} />
          ) : isCurrent ? (
            <div className="h-5 w-5 rounded-full border-2 border-blue-500 animate-pulse" />
          ) : (
            <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/25 hover:border-primary/50 transition-colors" />
          )}
        </button>

        {/* Title - acts as collapsible trigger */}
        <CollapsibleTrigger asChild disabled={!hasContent}>
          <button
            className={cn(
              "flex flex-1 items-center justify-between text-left min-w-0",
              hasContent && "hover:text-foreground/80 cursor-pointer",
              !hasContent && "cursor-default"
            )}
          >
            <span
              className={cn(
                "flex-1 text-[14px] leading-snug",
                done && "line-through text-muted-foreground",
                isCurrent && "text-foreground font-medium",
                upcoming && "text-muted-foreground"
              )}
            >
              {step.title}
            </span>
            {hasContent && !upcoming && (
              <ChevronDown
                className={cn(
                  "h-4 w-4 shrink-0 ml-2 text-muted-foreground/40 transition-transform duration-200",
                  open && "rotate-180"
                )}
              />
            )}
          </button>
        </CollapsibleTrigger>
      </div>

      {/* "Say done when ready" hint for current step */}
      {isCurrent && (
        <div className="px-4 pb-2 pl-12">
          <span className="text-xs text-blue-500/70 italic">
            Say &quot;done&quot; when ready
          </span>
        </div>
      )}

      {hasContent && (
        <CollapsibleContent>
          <div className="px-4 pb-3 pl-12 space-y-2">
            {step.description && (
              <p className="text-[13px] leading-relaxed text-muted-foreground">
                {step.description}
              </p>
            )}
            {step.warning && (
              <div className="flex items-start gap-2 rounded-lg bg-warning/10 px-3 py-2">
                <span className="text-[13px] text-warning">{step.warning}</span>
              </div>
            )}
          </div>
        </CollapsibleContent>
      )}
    </Collapsible>
  );
}

export function TaskProgressCard({
  steps,
  title = "Task progress",
  onToggleStep,
  onDismiss,
}: TaskProgressCardProps) {
  const [expanded, setExpanded] = useState(true);
  const completedCount = steps.filter((s) => s.status === "completed").length;
  const progressPercent = steps.length > 0 ? (completedCount / steps.length) * 100 : 0;

  return (
    <div className="relative rounded-2xl border border-border/60 bg-card overflow-hidden">
      {/* Gradient progress bar */}
      <div
        className="absolute top-0 left-0 h-[3px] bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500"
        style={{ width: `${progressPercent}%` }}
      />

      {/* Header */}
      <div className="flex w-full items-center justify-between px-4 py-3.5">
        <button
          onClick={() => setExpanded((o) => !o)}
          className="flex flex-1 items-center justify-between text-left transition-colors hover:opacity-80"
        >
          <span className="text-[15px] font-semibold text-foreground">
            {title}
          </span>

          <div className="flex items-center gap-2">
            <span className="text-[13px] text-muted-foreground tabular-nums">
              {completedCount} / {steps.length}
            </span>
            {expanded ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground/50" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground/50" />
            )}
          </div>
        </button>

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="ml-2 flex items-center justify-center rounded-full p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            aria-label="Exit guided mode"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Steps */}
      {expanded && (
        <div className="border-t border-border/40 py-1 overflow-y-auto scrollbar-hidden" style={{ maxHeight: '50vh' }}>
          {steps.map((step) => (
            <StepRow key={step.id} step={step} onToggle={() => onToggleStep?.(step.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
