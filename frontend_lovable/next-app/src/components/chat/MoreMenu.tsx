"use client";

import { useRef, useEffect, useCallback } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";
import { MenuItem } from "./MenuItem";
import { ProactivitySelector } from "./ProactivitySelector";
import { toast } from "sonner";

type ProactivityLevel = "low" | "medium" | "high";

interface MoreMenuProps {
  isOpen: boolean;
  onClose: () => void;
  showScreenShare: boolean;
  showTakePhoto: boolean;
  proactivity: ProactivityLevel;
  onProactivityChange: (level: ProactivityLevel) => void;
}

export function MoreMenu({
  isOpen,
  onClose,
  showScreenShare,
  showTakePhoto,
  proactivity,
  onProactivityChange,
}: MoreMenuProps) {
  const isMobile = useIsMobile();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      return () => document.removeEventListener("keydown", handleEscape);
    }
  }, [isOpen, handleEscape]);

  const handleAttachFile = () => {
    onClose();
    fileInputRef.current?.click();
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      toast(`Selected: ${file.name}`);
    }
  };

  const handleAction = (label: string) => {
    onClose();
    toast(`${label} — coming soon!`);
  };

  if (!isOpen) {
    return (
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept="image/*,.pdf,.doc,.docx"
        onChange={handleFileSelected}
      />
    );
  }

  const menuContent = (
    <>
      <MenuItem icon="📎" label="Attach file" onClick={handleAttachFile} />
      <div className="mx-4 border-t border-border" />
      {showScreenShare && (
        <MenuItem icon="🖥️" label="Share screen" onClick={() => handleAction("Share screen")} />
      )}
      {showTakePhoto && (
        <MenuItem icon="📷" label="Take photo" onClick={() => handleAction("Take photo")} />
      )}
      <div className="mx-4 border-t border-border" />
      <ProactivitySelector current={proactivity} onChange={onProactivityChange} />
    </>
  );

  if (isMobile) {
    // Bottom sheet
    return (
      <>
        <div
          className="fixed inset-0 z-40 bg-black/50 animate-fade-in"
          onClick={onClose}
          aria-hidden="true"
        />
        <div className="fixed inset-x-0 bottom-0 z-50 animate-slide-up">
          <div className="mx-2 mb-2 rounded-2xl bg-background border border-border overflow-hidden">
            {/* Drag handle */}
            <div className="flex justify-center pt-3 pb-1">
              <div className="h-1 w-10 rounded-full bg-muted-foreground/30" />
            </div>
            {menuContent}
          </div>
          <button
            onClick={onClose}
            className="mx-2 mb-[env(safe-area-inset-bottom,8px)] w-[calc(100%-16px)] rounded-2xl bg-background border border-border py-3 text-sm font-medium text-primary"
            aria-label="Cancel"
          >
            Cancel
          </button>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept="image/*,.pdf,.doc,.docx"
          onChange={handleFileSelected}
        />
      </>
    );
  }

  // Desktop popover
  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} aria-hidden="true" />
      <div className="absolute bottom-full left-0 z-50 mb-2 w-64 rounded-xl border border-border bg-background shadow-lg animate-scale-in origin-bottom-left">
        {menuContent}
      </div>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept="image/*,.pdf,.doc,.docx"
        onChange={handleFileSelected}
      />
    </>
  );
}
