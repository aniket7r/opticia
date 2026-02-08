import { isSameDay, subDays, format } from "date-fns";
import type { ChatSummary } from "./types";

interface ChatGroup {
  label: string;
  chats: ChatSummary[];
}

export function groupChatsByDate(chats: ChatSummary[]): ChatGroup[] {
  const groups: ChatGroup[] = [];
  const today = new Date();
  const yesterday = subDays(today, 1);
  const thisWeek = subDays(today, 7);

  const addToGroup = (label: string, chat: ChatSummary) => {
    const existing = groups.find((g) => g.label === label);
    if (existing) {
      existing.chats.push(chat);
    } else {
      groups.push({ label, chats: [chat] });
    }
  };

  chats.forEach((chat) => {
    const date = chat.createdAt;
    if (isSameDay(date, today)) {
      addToGroup("Today", chat);
    } else if (isSameDay(date, yesterday)) {
      addToGroup("Yesterday", chat);
    } else if (date > thisWeek) {
      addToGroup("This Week", chat);
    } else {
      addToGroup(format(date, "MMM d"), chat);
    }
  });

  return groups;
}
