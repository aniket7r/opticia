"use client";

import { useState } from "react";
import { Sparkles, Share2, MoreHorizontal, Pencil, Star, Trash2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

interface ChatHeaderProps {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  chatTitle?: string;
  isFavorite?: boolean;
  onRename?: (newTitle: string) => void;
  onToggleFavorite?: () => void;
}

export function ChatHeader({
  sidebarOpen,
  onToggleSidebar,
  chatTitle = "",
  isFavorite = false,
  onRename,
  onToggleFavorite,
}: ChatHeaderProps) {
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState(chatTitle);

  const handleOpenRename = () => {
    setRenameValue(chatTitle);
    setRenameOpen(true);
  };

  const handleConfirmRename = () => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== chatTitle) {
      onRename?.(trimmed);
      toast("Task renamed");
    }
    setRenameOpen(false);
  };

  return (
    <>
      <div className="flex items-center justify-end px-4 py-2 shrink-0">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-[13px] font-medium text-primary hover:text-primary"
            onClick={() => toast("Upgrade — releasing soon!")}
          >
            <Sparkles className="h-3.5 w-3.5" />
            Upgrade
          </Button>

          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-[13px] font-medium text-muted-foreground"
            onClick={() => toast("Share — releasing soon!")}
          >
            <Share2 className="h-3.5 w-3.5" />
            Share
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem onClick={handleOpenRename}>
                <Pencil className="h-4 w-4 mr-2" />
                Rename
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => {
                onToggleFavorite?.();
                toast(isFavorite ? "Removed from favorites" : "Added to favorites");
              }}>
                <Star className={`h-4 w-4 mr-2 ${isFavorite ? "fill-current text-warning" : ""}`} />
                {isFavorite ? "Remove favorite" : "Add to favorites"}
              </DropdownMenuItem>
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => toast.error("Delete — releasing soon!")}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Rename dialog */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Rename task</DialogTitle>
          </DialogHeader>
          <Input
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleConfirmRename()}
            placeholder="Task name"
            autoFocus
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setRenameOpen(false)}>Cancel</Button>
            <Button onClick={handleConfirmRename}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
