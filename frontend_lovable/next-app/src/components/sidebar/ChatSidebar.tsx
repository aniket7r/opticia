"use client";

import { useState, useEffect, useCallback } from "react";
import { PanelLeftClose, SquarePen, Search, Settings, Puzzle, Smartphone, FileText, ListTodo, PanelLeft, Filter, Star, Circle, CheckCircle2, PauseCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";
import { ChatCard } from "./ChatCard";
import { groupChatsByDate } from "./groupChatsByDate";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ChatSummary } from "./types";

interface ChatSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onOpen: () => void;
  chats: ChatSummary[];
  currentChatId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  isMobile: boolean;
  onSearchClick: () => void;
}

export function ChatSidebar({
  isOpen,
  onClose,
  onOpen,
  chats,
  currentChatId,
  onNewChat,
  onSelectChat,
  isMobile,
  onSearchClick,
}: ChatSidebarProps) {
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

  type FilterType = "all" | "active" | "completed" | "paused" | "favorites";
  const [filter, setFilter] = useState<FilterType>("all");

  const filteredChats = chats.filter((c) => {
    if (filter === "all") return true;
    if (filter === "favorites") return c.favorite;
    return c.status === filter;
  });

  const grouped = groupChatsByDate(filteredChats);

  const footerButtons = [
    { icon: Settings, label: "Settings" },
    { icon: Puzzle, label: "Personalisation" },
    { icon: Smartphone, label: "Download app" },
    { icon: FileText, label: "Docs" },
  ];

  const sidebarContent = (
    <div className="flex h-full flex-col pt-4">
      {/* Top icon column — same spacing as collapsed rail */}
      <div className="flex flex-col">
        {/* Logo row */}
        <div className="flex items-center h-8 mb-3">
          <div className="w-14 flex items-center justify-center shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background text-xs font-bold tracking-tight">
              Op
            </div>
          </div>
          <div className="flex-1 flex items-center justify-between pr-3">
            <span className="font-semibold text-foreground text-[15px] tracking-tight">Opticia</span>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  aria-label="Collapse sidebar"
                >
                  <PanelLeftClose className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">Close</TooltipContent>
            </Tooltip>
          </div>
        </div>

        {/* Nav icons — gap-1 matches collapsed rail */}
        <div className="flex flex-col gap-1">
          <button
            onClick={() => {
              onNewChat();
              if (isMobile) onClose();
            }}
            className="flex items-center w-full h-9 text-foreground hover:bg-accent rounded-lg transition-colors text-sm"
            aria-label="Start new chat"
          >
            <div className="w-14 flex items-center justify-center shrink-0">
              <SquarePen className="h-4 w-4 text-muted-foreground" />
            </div>
            <span>New task</span>
          </button>
          <button
            onClick={onSearchClick}
            className="flex items-center w-full h-9 text-foreground hover:bg-accent rounded-lg transition-colors text-sm"
            aria-label="Search chats"
          >
            <div className="w-14 flex items-center justify-center shrink-0">
              <Search className="h-4 w-4 text-muted-foreground" />
            </div>
            <span>Search</span>
          </button>
          <div className="flex items-center w-full h-9 text-foreground rounded-lg text-[13.5px]">
            <div className="w-14 flex items-center justify-center shrink-0">
              <ListTodo className="h-4 w-4 text-muted-foreground" />
            </div>
            <span className="flex-1 text-[11px] font-medium text-muted-foreground uppercase tracking-widest">
              {filter === "all" ? "All tasks" : filter === "favorites" ? "Favorites" : `${filter}`}
            </span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className={cn(
                    "p-1.5 rounded-lg transition-colors mr-1",
                    filter !== "all"
                      ? "text-foreground bg-accent"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent"
                  )}
                  aria-label="Filter tasks"
                >
                  <Filter className="h-3.5 w-3.5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-40">
                {(["all", "active", "completed", "paused", "favorites"] as FilterType[]).map((f) => (
                  <DropdownMenuItem
                    key={f}
                    onClick={() => setFilter(f)}
                    className={cn(filter === f && "bg-accent font-medium")}
                  >
                    {f === "all" && <><ListTodo className="h-3.5 w-3.5 mr-2" />All tasks</>}
                    {f === "active" && <><Circle className="h-3.5 w-3.5 mr-2" />Active</>}
                    {f === "completed" && <><CheckCircle2 className="h-3.5 w-3.5 mr-2" />Completed</>}
                    {f === "paused" && <><PauseCircle className="h-3.5 w-3.5 mr-2" />Paused</>}
                    {f === "favorites" && <><Star className="h-3.5 w-3.5 mr-2" />Favorites</>}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto px-3">
        {grouped.map((group) => (
          <div key={group.label} className="mb-1">
            <span className="block px-2 pt-3 pb-1 text-[11px] font-medium text-muted-foreground/70 uppercase tracking-widest">
              {group.label}
            </span>
            {group.chats.map((chat) => (
              <ChatCard
                key={chat.id}
                chat={chat}
                isActive={chat.id === currentChatId}
                onClick={() => {
                  onSelectChat(chat.id);
                  if (isMobile) onClose();
                }}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Footer with icon buttons */}
      <div className="border-t border-border px-4 py-3 flex items-center justify-between">
        {footerButtons.map(({ icon: Icon, label }) => (
          <Tooltip key={label}>
            <TooltipTrigger asChild>
              <button
                onClick={() => toast(`${label} — releasing soon!`)}
                className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                aria-label={label}
              >
                <Icon className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top">{label}</TooltipContent>
          </Tooltip>
        ))}
      </div>
    </div>
  );

  // Desktop: persistent inline sidebar
  if (!isMobile) {
    if (!isOpen) {
      // Collapsed icon rail
      return (
        <aside className="w-14 shrink-0 border-r border-border bg-sidebar h-full flex flex-col items-center pt-4">
          {/* Logo */}
          <button
            onClick={onOpen}
            className="group flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background text-xs font-bold tracking-tight transition-colors hover:bg-foreground/80 mb-3"
            aria-label="Open sidebar"
          >
            <span className="group-hover:hidden">Op</span>
            <PanelLeft className="h-4 w-4 hidden group-hover:block" />
          </button>

          {/* Nav icons — gap-1 and h-9 match open state */}
          <div className="flex flex-col items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={onNewChat}
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                  aria-label="New task"
                >
                  <SquarePen className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">New task</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={onSearchClick}
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                  aria-label="Search"
                >
                  <Search className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">Search</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={onOpen}
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                  aria-label="All tasks"
                >
                  <ListTodo className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right">All tasks</TooltipContent>
            </Tooltip>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Bottom icons */}
          <div className="flex flex-col items-center gap-1">
            {footerButtons.map(({ icon: Icon, label }) => (
              <Tooltip key={label}>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => toast(`${label} — releasing soon!`)}
                    className="p-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                    aria-label={label}
                  >
                    <Icon className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right">{label}</TooltipContent>
              </Tooltip>
            ))}
          </div>
        </aside>
      );
    }
    return (
      <aside className="w-[280px] shrink-0 border-r border-border bg-sidebar h-full">
        {sidebarContent}
      </aside>
    );
  }

  // Mobile: G3 logo button when closed, overlay sidebar when open
  return (
    <>
      {/* Floating G3 logo to reopen sidebar */}
      {!isOpen && (
        <button
          onClick={onOpen}
          className="fixed top-4 left-4 z-40 flex h-9 w-9 items-center justify-center rounded-lg bg-foreground text-background text-xs font-bold tracking-tight shadow-lg active:scale-95 transition-transform"
          aria-label="Open sidebar"
        >
          Op
        </button>
      )}

      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/40 z-40 transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sidebar panel — same styling as desktop */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 w-[280px] border-r border-border bg-sidebar z-50 flex flex-col shadow-xl",
          "transform transition-transform duration-300 ease-out",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
        role="dialog"
        aria-modal="true"
        aria-label="Chat history sidebar"
      >
        {sidebarContent}
      </div>
    </>
  );
}
