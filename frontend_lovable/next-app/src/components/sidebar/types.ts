export interface ChatSummary {
  id: string;
  title: string;
  status: "active" | "completed" | "paused";
  createdAt: Date;
  taskCompleted?: boolean;
  duration?: number; // minutes
  lastMessage?: string;
  favorite?: boolean;
}
