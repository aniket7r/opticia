"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface LargePreviewProps {
  children: ReactNode;
  className?: string;
}

export function LargePreview({ children, className }: LargePreviewProps) {
  return (
    <div className={cn("relative flex-1 overflow-hidden animate-fade-in", className)}>
      {children}
    </div>
  );
}
