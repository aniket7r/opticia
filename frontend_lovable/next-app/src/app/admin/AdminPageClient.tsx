"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCw, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { adminApi, DashboardStats, Session as ApiSession } from "@/lib/api";

// Types
interface Metrics {
  activeSessions: number;
  apiCostToday: number;
  cacheHitRate: number;
  avgSessionDuration: number;
  fallbacksToday: number;
  toolCallsToday: number;
  errorsToday: number;
  tokensToday: number;
  toolUsage: Record<string, number>;
}

interface Session {
  id: string;
  startedAt: Date;
  endedAt: Date | null;
  duration: number | null;
  status: "active" | "completed" | "error";
  toolCallsCount: number;
}

// MetricCard
interface MetricCardProps {
  label: string;
  value: string | number;
  sublabel: string;
  color?: "default" | "success" | "warning" | "error";
}

function MetricCard({ label, value, sublabel, color = "default" }: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4 transition-colors",
        color === "success" && "border-success/30 bg-success/5",
        color === "warning" && "border-warning/30 bg-warning/5",
        color === "error" && "border-destructive/30 bg-destructive/5",
        color === "default" && "border-border bg-card"
      )}
    >
      <div className="text-sm text-muted-foreground mb-1">{label}</div>
      <div className="text-2xl font-bold text-foreground">{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{sublabel}</div>
    </div>
  );
}

// SessionStatusBadge
function SessionStatusBadge({ status }: { status: Session["status"] }) {
  const config = {
    active: { label: "Active", icon: "🟢", className: "text-success" },
    completed: { label: "Done", icon: "✅", className: "text-success" },
    error: { label: "Error", icon: "❌", className: "text-destructive" },
  };
  const c = config[status];
  return (
    <span className={cn("inline-flex items-center gap-1 text-sm", c.className)}>
      <span>{c.icon}</span>
      <span>{c.label}</span>
    </span>
  );
}

// Main
const AdminPageClient = () => {
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<Metrics>({
    activeSessions: 0,
    apiCostToday: 0,
    cacheHitRate: 0,
    avgSessionDuration: 0,
    fallbacksToday: 0,
    toolCallsToday: 0,
    errorsToday: 0,
    tokensToday: 0,
    toolUsage: {},
  });

  const [sessions, setSessions] = useState<Session[]>([]);

  const fetchData = useCallback(async () => {
    try {
      setError(null);

      // Fetch stats and sessions in parallel
      const [statsData, sessionsData] = await Promise.all([
        adminApi.getStats(),
        adminApi.getSessions(10),
      ]);

      // Map stats to metrics
      setMetrics({
        activeSessions: statsData.active_sessions,
        apiCostToday: statsData.total_cost_today,
        cacheHitRate: statsData.cache_hit_rate,
        avgSessionDuration: statsData.avg_session_duration,
        fallbacksToday: statsData.fallback_count_today,
        toolCallsToday: Object.values(statsData.tool_usage).reduce((a, b) => a + b, 0),
        errorsToday: statsData.error_count_today,
        tokensToday: statsData.total_tokens_today,
        toolUsage: statsData.tool_usage,
      });

      // Map sessions
      setSessions(
        sessionsData.map((s: ApiSession) => ({
          id: s.id,
          startedAt: new Date(s.created_at),
          endedAt: s.ended_at ? new Date(s.ended_at) : null,
          duration: s.ended_at
            ? Math.round((new Date(s.ended_at).getTime() - new Date(s.created_at).getTime()) / 60000)
            : null,
          status: s.status === "error" ? "error" : s.ended_at ? "completed" : "active",
          toolCallsCount: s.tool_calls_count,
        }))
      );

      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to fetch admin data:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="min-h-[calc(100vh-3.5rem)] bg-background p-4 md:p-6 animate-fade-in">
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="tap-target flex items-center justify-center rounded-lg p-2 hover:bg-muted transition-colors"
            aria-label="Back to app"
          >
            <ArrowLeft className="h-5 w-5 text-foreground" />
          </Link>
          <h1 className="text-xl md:text-2xl font-bold text-foreground">Admin Dashboard</h1>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
          <span className="hidden sm:inline">Auto-refresh: 30s</span>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <p className="text-sm text-destructive">{error}</p>
          <button
            onClick={fetchData}
            className="ml-auto text-sm font-medium text-destructive hover:underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
        <MetricCard
          label="Sessions"
          value={metrics.activeSessions}
          sublabel="🟢 active"
          color="success"
        />
        <MetricCard
          label="API Cost"
          value={`$${metrics.apiCostToday.toFixed(2)}`}
          sublabel="today"
        />
        <MetricCard
          label="Cache Hit"
          value={`${metrics.cacheHitRate.toFixed(1)}%`}
          sublabel="rate"
          color={metrics.cacheHitRate > 80 ? "success" : "warning"}
        />
        <MetricCard
          label="Avg Session"
          value={`${metrics.avgSessionDuration.toFixed(1)} min`}
          sublabel="duration"
        />
        <MetricCard
          label="Fallbacks"
          value={metrics.fallbacksToday}
          sublabel="today"
          color={metrics.fallbacksToday > 10 ? "warning" : "default"}
        />
        <MetricCard
          label="Tool Calls"
          value={metrics.toolCallsToday}
          sublabel="today"
        />
      </div>

      {/* Additional Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <MetricCard
          label="Errors"
          value={metrics.errorsToday}
          sublabel="today"
          color={metrics.errorsToday > 0 ? "error" : "default"}
        />
        <MetricCard
          label="Tokens"
          value={metrics.tokensToday.toLocaleString()}
          sublabel="today"
        />
        {Object.entries(metrics.toolUsage).slice(0, 2).map(([tool, count]) => (
          <MetricCard
            key={tool}
            label={tool.replace(/_/g, " ")}
            value={count}
            sublabel="calls"
          />
        ))}
      </div>

      {/* Sessions Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="font-medium text-foreground">Recent Sessions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-left text-sm text-muted-foreground">
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Tools</th>
              </tr>
            </thead>
            <tbody>
              {sessions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                    {isLoading ? "Loading..." : "No sessions yet"}
                  </td>
                </tr>
              ) : (
                sessions.map((s) => (
                  <tr
                    key={s.id}
                    className="border-b border-border last:border-0 hover:bg-muted/50 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-sm text-foreground">
                      {s.id.slice(0, 8)}…
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatDistanceToNow(s.startedAt)} ago
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {s.duration ? (
                        `${s.duration} min`
                      ) : (
                        <span className="text-primary font-medium">active</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <SessionStatusBadge status={s.status} />
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">{s.toolCallsCount}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-8 flex flex-col sm:flex-row justify-between items-center gap-4 text-sm text-muted-foreground">
        <Link
          href="/"
          className="flex items-center gap-2 hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to App
        </Link>
        <span>
          Last updated:{" "}
          {lastUpdated.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          })}
        </span>
      </footer>
    </div>
  );
};

export default AdminPageClient;
