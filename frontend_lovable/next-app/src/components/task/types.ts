export interface Step {
  id: string;
  title: string;
  description?: string;
  status: "completed" | "current" | "upcoming";
  warning?: string;
  toggleable?: boolean;
}

export interface TaskData {
  id: string;
  title: string;
  summary: string;
  estimatedTime?: string;
  steps: Step[];
  currentStep: number;
}
