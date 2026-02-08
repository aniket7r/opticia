"use client";

import { cn } from "@/lib/utils";

const statusConfig = {
  active: { icon: "🟢", label: "Active", className: "text-success" },
  completed: { icon: "✅", label: "Done", className: "text-success" },
  paused: { icon: "⏸️", label: "Paused", className: "text-muted-foreground" },
};

interface ChatStatusBadgeProps {
  status: "active" | "completed" | "paused";
}

export function ChatStatusBadge({ status }: ChatStatusBadgeProps) {
  const config = statusConfig[status];
  return (
    <span className={cn("text-xs flex items-center gap-1", config.className)}>
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
