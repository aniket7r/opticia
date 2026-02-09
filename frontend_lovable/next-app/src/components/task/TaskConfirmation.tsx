"use client";

import { ListChecks } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import type { Step } from "./types";

interface TaskConfirmationProps {
  open: boolean;
  title: string;
  steps: Step[];
  onAccept: () => void;
  onDecline: () => void;
}

export function TaskConfirmation({
  open,
  title,
  steps,
  onAccept,
  onDecline,
}: TaskConfirmationProps) {
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onDecline()}>
      <DialogContent className="max-w-sm gap-4">
        <DialogHeader className="items-center text-center">
          <div className="mx-auto mb-1 flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10">
            <ListChecks className="h-6 w-6 text-blue-500" />
          </div>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            {steps.length} steps &mdash; Ready to get started?
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-40 overflow-y-auto space-y-1.5 rounded-lg border border-border/40 bg-muted/30 p-3">
          {steps.map((s, i) => (
            <div key={s.id} className="flex items-start gap-2 text-sm text-muted-foreground">
              <span className="shrink-0 text-xs font-mono text-muted-foreground/50 mt-0.5 w-4 text-right">
                {i + 1}.
              </span>
              <span className="leading-snug">{s.title}</span>
            </div>
          ))}
        </div>

        <DialogFooter className="flex-row gap-2 sm:gap-2">
          <button
            onClick={onDecline}
            className="flex-1 rounded-lg border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-accent"
          >
            Just explain
          </button>
          <button
            onClick={onAccept}
            className="flex-1 rounded-lg bg-blue-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-600"
          >
            Guide me
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
