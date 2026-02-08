"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Check, ChevronUp, ChevronDown, Loader2 } from "lucide-react";

export interface ThinkingSubStep {
  icon?: string;
  text: string;
  status: "pending" | "active" | "complete";
}

export interface ThinkingStepData {
  icon: string;
  text: string;
  status: "pending" | "active" | "complete";
  timestamp?: string;
  description?: string;
  subSteps?: ThinkingSubStep[];
}

interface ThinkingStepProps {
  step: ThinkingStepData;
  index: number;
  isLast: boolean;
}

export function ThinkingStep({ step, index, isLast }: ThinkingStepProps) {
  const [expanded, setExpanded] = useState(step.status === "active");
  const hasExpandableContent = step.description || (step.subSteps && step.subSteps.length > 0);

  return (
    <div
      className="animate-fade-in"
      style={{ animationDelay: `${index * 100}ms`, animationFillMode: "both" }}
    >
      {/* Main step row */}
      <div className="flex items-start gap-3">
        {/* Timeline indicator */}
        <div className="flex flex-col items-center pt-0.5">
          <div
            className={cn(
              "flex h-5 w-5 shrink-0 items-center justify-center rounded-full transition-all duration-300",
              step.status === "complete" && "bg-foreground/10",
              step.status === "active" && "bg-primary/15 ring-2 ring-primary/30",
              step.status === "pending" && "bg-muted"
            )}
          >
            {step.status === "complete" && (
              <Check className="h-3 w-3 text-foreground/60" />
            )}
            {step.status === "active" && (
              <Loader2 className="h-3 w-3 text-primary animate-spin" />
            )}
            {step.status === "pending" && (
              <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30" />
            )}
          </div>
          {!isLast && (
            <div
              className={cn(
                "w-px flex-1 min-h-[16px] mt-1",
                step.status === "complete" ? "bg-foreground/10" : "bg-border"
              )}
            />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 pb-3">
          <button
            onClick={() => hasExpandableContent && setExpanded(!expanded)}
            className={cn(
              "flex w-full items-center gap-2 text-left",
              hasExpandableContent && "cursor-pointer group"
            )}
            disabled={!hasExpandableContent}
          >
            <span
              className={cn(
                "text-[13px] font-medium leading-tight flex-1 transition-colors",
                step.status === "complete" && "text-foreground/70",
                step.status === "active" && "text-foreground",
                step.status === "pending" && "text-muted-foreground/50",
                hasExpandableContent && "group-hover:text-foreground"
              )}
            >
              {step.text}
            </span>

            <div className="flex items-center gap-2 shrink-0">
              {step.timestamp && (
                <span className="text-[11px] text-muted-foreground/50 tabular-nums">
                  {step.timestamp}
                </span>
              )}
              {hasExpandableContent && (
                expanded
                  ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground/40" />
                  : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground/40" />
              )}
            </div>
          </button>

          {/* Expanded content */}
          {expanded && hasExpandableContent && (
            <div className="mt-2 space-y-2 animate-fade-in">
              {step.description && (
                <p className="text-[12.5px] leading-relaxed text-muted-foreground/70 pl-0.5">
                  {step.description}
                </p>
              )}
              {step.subSteps && step.subSteps.length > 0 && (
                <div className="flex flex-col gap-1.5 mt-1.5">
                  {step.subSteps.map((sub, i) => (
                    <div
                      key={i}
                      className={cn(
                        "flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2 text-[12.5px] transition-all",
                        sub.status === "complete" && "text-foreground/60",
                        sub.status === "active" && "text-foreground bg-primary/5 ring-1 ring-primary/10",
                        sub.status === "pending" && "text-muted-foreground/40"
                      )}
                    >
                      {sub.status === "complete" && (
                        <div className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-foreground/8">
                          <Check className="h-2.5 w-2.5 text-foreground/50" />
                        </div>
                      )}
                      {sub.status === "active" && (
                        <Loader2 className="h-3.5 w-3.5 shrink-0 text-primary animate-spin" />
                      )}
                      {sub.status === "pending" && (
                        <div className="h-4 w-4 shrink-0 flex items-center justify-center">
                          <div className="h-1 w-1 rounded-full bg-muted-foreground/30" />
                        </div>
                      )}
                      <span className="flex-1">{sub.text}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
