"use client";

import { X, FileDown } from "lucide-react";
import type { ReportData } from "@/hooks/useChat";
import { ReportGenerating } from "./ReportGenerating";
import { ReportDownload } from "./ReportDownload";

interface ReportPanelProps {
  report: ReportData;
  onDismiss: () => void;
  apiBaseUrl?: string;
}

export function ReportPanel({ report, onDismiss, apiBaseUrl }: ReportPanelProps) {
  if (report.status === "generating") {
    return (
      <div className="flex h-full flex-col">
        <ReportHeader topic={report.topic} onDismiss={onDismiss} />
        <ReportGenerating topic={report.topic} estimatedSeconds={report.estimatedSeconds} />
      </div>
    );
  }

  if (report.status === "error") {
    return (
      <div className="flex h-full flex-col">
        <ReportHeader topic={report.topic} onDismiss={onDismiss} />
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="text-center">
            <p className="text-sm text-destructive mb-2">Failed to generate report</p>
            <p className="text-xs text-muted-foreground">{report.error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <ReportHeader topic={report.topic} onDismiss={onDismiss}>
        {report.markdownContent && (
          <ReportDownload
            markdownContent={report.markdownContent}
            topic={report.topic}
            apiBaseUrl={apiBaseUrl}
          />
        )}
      </ReportHeader>

      {/* Scrollable report content */}
      <div className="flex-1 overflow-y-auto p-4">
        {report.htmlContent ? (
          <div
            className="prose prose-sm dark:prose-invert max-w-none
              prose-headings:text-foreground prose-p:text-foreground/90
              prose-strong:text-foreground prose-li:text-foreground/90
              prose-table:text-sm prose-th:bg-muted/50 prose-th:p-2 prose-td:p-2
              prose-th:border prose-td:border prose-th:border-border prose-td:border-border
              prose-code:bg-muted prose-code:px-1 prose-code:rounded
              prose-a:text-primary"
            dangerouslySetInnerHTML={{ __html: report.htmlContent }}
          />
        ) : (
          <pre className="whitespace-pre-wrap text-sm text-foreground/80">
            {report.markdownContent}
          </pre>
        )}
      </div>
    </div>
  );
}

function ReportHeader({
  topic,
  onDismiss,
  children,
}: {
  topic: string;
  onDismiss: () => void;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
      <div className="flex items-center gap-2 min-w-0">
        <FileDown className="h-4 w-4 text-primary shrink-0" />
        <h3 className="text-sm font-medium truncate">{topic}</h3>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {children}
        <button
          onClick={onDismiss}
          className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          aria-label="Close report"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
