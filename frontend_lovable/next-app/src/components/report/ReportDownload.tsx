"use client";

import { useState } from "react";
import { Download, FileText, File } from "lucide-react";

interface ReportDownloadProps {
  markdownContent: string;
  topic: string;
  apiBaseUrl?: string;
}

export function ReportDownload({ markdownContent, topic, apiBaseUrl }: ReportDownloadProps) {
  const [downloading, setDownloading] = useState<"docx" | "pdf" | null>(null);

  const handleDownload = async (format: "docx" | "pdf") => {
    setDownloading(format);

    try {
      const baseUrl = apiBaseUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
      const response = await fetch(`${baseUrl}/reports/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          markdown_content: markdownContent,
          format,
          topic,
        }),
      });

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      // Download the file
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const safeTopic = topic.replace(/[^a-zA-Z0-9 _-]/g, "").substring(0, 50).trim() || "report";
      a.href = url;
      a.download = `${safeTopic}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error(`Failed to download ${format}:`, error);
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => handleDownload("docx")}
        disabled={downloading !== null}
        className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
        title="Download as DOCX"
      >
        {downloading === "docx" ? (
          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
        ) : (
          <FileText className="h-3.5 w-3.5" />
        )}
        DOCX
      </button>

      <button
        onClick={() => handleDownload("pdf")}
        disabled={downloading !== null}
        className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
        title="Download as PDF"
      >
        {downloading === "pdf" ? (
          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
        ) : (
          <File className="h-3.5 w-3.5" />
        )}
        PDF
      </button>
    </div>
  );
}
