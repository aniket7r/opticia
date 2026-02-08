"use client";

import { useRef, useState, useCallback, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Minimize2, Camera } from "lucide-react";

interface FloatingPiPProps {
  children: ReactNode;
  onTap?: () => void;
  isTaskMode?: boolean;
  isCameraActive?: boolean;
  sidebarOpen?: boolean;
}

type Corner = "top-left" | "top-right" | "bottom-left" | "bottom-right";

const cornerPositions = (sidebarOpen: boolean): Record<Corner, { top?: string; bottom?: string; left?: string; right?: string }> => {
  const leftOffset = sidebarOpen ? "296px" : "72px";
  return {
    "top-left": { top: "80px", left: leftOffset },
    "top-right": { top: "80px", right: "16px" },
    "bottom-left": { bottom: "100px", left: leftOffset },
    "bottom-right": { bottom: "100px", right: "16px" },
  };
};

export function FloatingPiP({ children, onTap, isTaskMode = false, isCameraActive = false, sidebarOpen = false }: FloatingPiPProps) {
  const [corner, setCorner] = useState<Corner>("bottom-left");
  const [dragging, setDragging] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [minimized, setMinimized] = useState(false);
  const pipRef = useRef<HTMLDivElement>(null);
  const dragStart = useRef<{ x: number; y: number; startX: number; startY: number } | null>(null);
  const hasMoved = useRef(false);

  const snapToCorner = useCallback(() => {
    if (!pipRef.current) return;
    const rect = pipRef.current.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    const isLeft = cx < vw / 2;
    const isTop = cy < vh / 2;

    const newCorner: Corner = isTop
      ? isLeft ? "top-left" : "top-right"
      : isLeft ? "bottom-left" : "bottom-right";

    setCorner(newCorner);
    setPos(null);
  }, []);

  const handlePointerDown = (e: React.PointerEvent) => {
    if (!pipRef.current) return;
    const rect = pipRef.current.getBoundingClientRect();
    dragStart.current = { x: e.clientX, y: e.clientY, startX: rect.left, startY: rect.top };
    hasMoved.current = false;
    setDragging(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!dragStart.current || !dragging) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) hasMoved.current = true;
    setPos({ x: dragStart.current.startX + dx, y: dragStart.current.startY + dy });
  };

  const handlePointerUp = () => {
    setDragging(false);
    if (hasMoved.current) {
      snapToCorner();
    }
    dragStart.current = null;
  };

  const positions = cornerPositions(sidebarOpen);
  const style: React.CSSProperties = pos
    ? { position: "fixed", left: pos.x, top: pos.y, transition: dragging ? "none" : "all 0.3s cubic-bezier(.4,0,.2,1)" }
    : { position: "fixed", ...positions[corner], transition: "all 0.3s cubic-bezier(.4,0,.2,1)" };

  return (
    <div
      ref={pipRef}
      className={cn(
        "z-40 cursor-grab select-none overflow-hidden shadow-xl shadow-black/20",
        minimized
          ? `w-[52px] h-[52px] rounded-full ring-2 ring-violet-400/30 shadow-lg shadow-violet-500/25 ${isCameraActive ? "animate-pulse" : ""}`
          : "w-[22vw] max-w-[200px] min-w-[100px] aspect-[3/4] rounded-2xl ring-1 ring-black/10",
        dragging && "cursor-grabbing scale-105 shadow-2xl",
        !minimized && isTaskMode && "scale-90"
      )}
      style={style}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onClickCapture={(e) => {
        if (hasMoved.current) {
          e.stopPropagation();
          e.preventDefault();
          hasMoved.current = false;
        }
      }}
      role="region"
      aria-label={minimized ? "Restore camera preview" : "Camera preview"}
      tabIndex={-1}
    >
      {minimized ? (
        <button
          className="flex h-full w-full items-center justify-center bg-gradient-to-br from-violet-500 to-indigo-600 rounded-full"
          onClick={(e) => {
            e.stopPropagation();
            if (!hasMoved.current) setMinimized(false);
          }}
          aria-label="Restore camera preview"
        >
          <Camera className="h-5 w-5 text-white drop-shadow-md" />
        </button>
      ) : (
        <div className="relative h-full w-full">
          <button
            className="absolute left-1.5 top-1.5 z-50 flex h-6 w-6 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur-sm transition-colors hover:bg-black/60"
            onClick={(e) => {
              e.stopPropagation();
              setMinimized(true);
            }}
            aria-label="Minimize camera preview"
          >
            <Minimize2 className="h-3.5 w-3.5" />
          </button>
          {children}
        </div>
      )}
    </div>
  );
}
