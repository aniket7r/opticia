"use client";

import { cn } from "@/lib/utils";

interface MenuItemProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  hasSubmenu?: boolean;
}

export function MenuItem({ icon, label, onClick, hasSubmenu }: MenuItemProps) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm text-foreground transition-colors hover:bg-muted tap-target"
      aria-label={label}
    >
      <span className="text-base shrink-0">{icon}</span>
      <span className="flex-1 text-left">{label}</span>
      {hasSubmenu && (
        <span className="text-muted-foreground">▶</span>
      )}
    </button>
  );
}
