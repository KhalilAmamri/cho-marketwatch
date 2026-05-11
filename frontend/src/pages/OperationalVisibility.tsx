import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import { getOperationLogs, getOperationalVisibility, resolveStorageUrl, retryFailedRawNow } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Cell } from "recharts";
import { ShieldCheck, Database, AlertTriangle, Activity, Camera, ExternalLink, RotateCw, RefreshCcw } from "lucide-react";
import { toast } from "sonner";

import type { OperationalFailedRow } from "@/lib/api";

const ALERT_ACK_STORAGE_KEY = "cho_ops_acknowledged_alerts_v1";
const ALERT_ACK_CHANGE_EVENT = "cho-ops-alert-ack-changed";

type LogStatusFilter = "all" | "processed" | "failed" | "pending";
type FailedAlertsScope = "active" | "all";
type AlertAcknowledgementMap = Record<string, string>;

type FailedAlertGroup = {
  alertKey: string;
  storeName: string;
  productLabel: string;
  errorMessage: string | null;
  httpStatusCode: number | null;
  firstSeenAt: string;
  lastSeenAt: string;
  firstSeenMs: number;
  lastSeenMs: number;
  occurrenceCount: number;
  latestRowId: number;
  latestScreenshotPath: string | null;
};

function loadAlertAcknowledgements(): AlertAcknowledgementMap {
  if (typeof window === "undefined") return {};

  try {
    const raw = window.localStorage.getItem(ALERT_ACK_STORAGE_KEY);
    if (!raw) return {};

    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};

    const acknowledgements: AlertAcknowledgementMap = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof value === "string") acknowledgements[key] = value;
    }

    return acknowledgements;
  } catch {
    return {};
  }
}

function saveAlertAcknowledgements(value: AlertAcknowledgementMap): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ALERT_ACK_STORAGE_KEY, JSON.stringify(value));
  window.dispatchEvent(new Event(ALERT_ACK_CHANGE_EVENT));
}

function buildAlertKey(row: OperationalFailedRow): string {
  const storeName = (row.storeName || "unknown-store").trim().toLowerCase();
  const productLabel = (row.productLabel || "unknown-target").trim().toLowerCase();
  const errorMessage = (row.errorMessage || "unknown-error").trim().toLowerCase();
  const httpCode = row.httpStatusCode === null ? "no-http" : String(row.httpStatusCode);
  return `${storeName}|${productLabel}|${httpCode}|${errorMessage}`;
}

function toTimestamp(value: string): number {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function groupFailedAlerts(rows: OperationalFailedRow[]): FailedAlertGroup[] {
  const groups = new Map<string, FailedAlertGroup>();

  for (const row of rows) {
    const alertKey = buildAlertKey(row);
    const scrapedAtMs = toTimestamp(row.scrapedAt);
    const existing = groups.get(alertKey);

    if (!existing) {
      groups.set(alertKey, {
        alertKey,
        storeName: row.storeName,
        productLabel: row.productLabel,
        errorMessage: row.errorMessage,
        httpStatusCode: row.httpStatusCode,
        firstSeenAt: row.scrapedAt,
        lastSeenAt: row.scrapedAt,
        firstSeenMs: scrapedAtMs,
        lastSeenMs: scrapedAtMs,
        occurrenceCount: 1,
        latestRowId: row.id,
        latestScreenshotPath: row.screenshotPath,
      });
      continue;
    }

    existing.occurrenceCount += 1;

    if (scrapedAtMs < existing.firstSeenMs) {
      existing.firstSeenMs = scrapedAtMs;
      existing.firstSeenAt = row.scrapedAt;
    }

    if (scrapedAtMs > existing.lastSeenMs || (scrapedAtMs === existing.lastSeenMs && row.id > existing.latestRowId)) {
      existing.lastSeenMs = scrapedAtMs;
      existing.lastSeenAt = row.scrapedAt;
      existing.latestRowId = row.id;
      existing.latestScreenshotPath = row.screenshotPath;
      existing.storeName = row.storeName;
      existing.productLabel = row.productLabel;
      existing.errorMessage = row.errorMessage;
      existing.httpStatusCode = row.httpStatusCode;
    }
  }

  return [...groups.values()].sort((a, b) => b.lastSeenMs - a.lastSeenMs);
}

function isAlertActive(group: FailedAlertGroup, acknowledgements: AlertAcknowledgementMap): boolean {
  const acknowledgedSeenAt = acknowledgements[group.alertKey];
  if (!acknowledgedSeenAt) return true;

  return group.lastSeenMs > toTimestamp(acknowledgedSeenAt);
}

export default function OperationalVisibility() {
  const queryClient = useQueryClient();
  const [retryRowId, setRetryRowId] = useState<number | null>(null);
  const [alertAcknowledgements, setAlertAcknowledgements] = useState<AlertAcknowledgementMap>(() => loadAlertAcknowledgements());
  const [failedAlertsScope, setFailedAlertsScope] = useState<FailedAlertsScope>("active");
  const [failedAlertsSearch, setFailedAlertsSearch] = useState("");
  const [logsStatusFilter, setLogsStatusFilter] = useState<LogStatusFilter>("all");
  const [logsSearch, setLogsSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["operational-visibility"],
    queryFn: () => getOperationalVisibility(200),
  });

  const { data: operationLogs = [], isLoading: logsLoading } = useQuery({
    queryKey: ["operations-logs"],
    queryFn: () => getOperationLogs(200),
  });

  const retryMutation = useMutation({
    mutationFn: (rawStagingId: number) => retryFailedRawNow(rawStagingId, false),
    onMutate: (rawStagingId) => {
      setRetryRowId(rawStagingId);
    },
    onSuccess: (result) => {
      if (result.rawRow.status === "failed") {
        toast.error(result.rawRow.errorMessage || "Retry operation finished with failure");
      } else {
        toast.success(result.message);
      }
      queryClient.invalidateQueries({ queryKey: ["operational-visibility"] });
      queryClient.invalidateQueries({ queryKey: ["operations-logs"] });
    },
    onError: (error: any) => {
      if (error?.code === "ECONNABORTED") {
        toast.error("Retry is taking longer than expected. Please wait and refresh the operations log.");
        return;
      }
      toast.error(error?.response?.data?.detail || "Failed to retry scraping row");
    },
    onSettled: () => {
      setRetryRowId(null);
    },
  });

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === ALERT_ACK_STORAGE_KEY) {
        setAlertAcknowledgements(loadAlertAcknowledgements());
      }
    };

    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const failedAlertGroups = useMemo(
    () => groupFailedAlerts(data?.failedRows || []),
    [data?.failedRows],
  );

  const activeFailedAlertGroups = useMemo(
    () => failedAlertGroups.filter((group) => isAlertActive(group, alertAcknowledgements)),
    [failedAlertGroups, alertAcknowledgements],
  );

  const updateAlertAcknowledgements = (updater: (previous: AlertAcknowledgementMap) => AlertAcknowledgementMap) => {
    setAlertAcknowledgements((previous) => {
      const next = updater(previous);
      saveAlertAcknowledgements(next);
      return next;
    });
  };

  const acknowledgeAlert = (group: FailedAlertGroup) => {
    updateAlertAcknowledgements((previous) => ({
      ...previous,
      [group.alertKey]: group.lastSeenAt,
    }));
    toast.success("Notification dismissed and hidden.");
  };

  const acknowledgeAllActiveAlerts = () => {
    if (!activeFailedAlertGroups.length) return;

    updateAlertAcknowledgements((previous) => {
      const next = { ...previous };
      for (const group of activeFailedAlertGroups) {
        next[group.alertKey] = group.lastSeenAt;
      }
      return next;
    });
    toast.success(`${activeFailedAlertGroups.length} alert${activeFailedAlertGroups.length === 1 ? "" : "s"} dismissed.`);
  };

  const restoreAcknowledgedAlert = (group: FailedAlertGroup) => {
    updateAlertAcknowledgements((previous) => {
      const { [group.alertKey]: _, ...rest } = previous;
      return rest;
    });
    toast.success("Alert restored to active notifications.");
  };

  const statusData = useMemo(() => {
    const rows = data?.statusCodeCounts || [];
    return rows.map((row) => ({
      statusLabel: String(row.statusCode),
      count: row.count,
      color: row.statusCode === 200 ? "hsl(var(--cho-teal))" : "hsl(var(--destructive))",
    }));
  }, [data]);

  const totalRecords = data?.totalRecords || 0;
  const failedRequests = data?.failedRequests || 0;
  const successRate = data?.successRate || 0;
  const activeAlertsCount = activeFailedAlertGroups.length;

  const visibleFailedAlertGroups = useMemo(() => {
    const source = failedAlertsScope === "all" ? failedAlertGroups : activeFailedAlertGroups;
    const search = failedAlertsSearch.trim().toLowerCase();
    if (!search) return source;

    return source.filter((group) => (
      group.storeName.toLowerCase().includes(search)
      || group.productLabel.toLowerCase().includes(search)
      || (group.errorMessage || "").toLowerCase().includes(search)
      || (group.httpStatusCode !== null && String(group.httpStatusCode).includes(search))
    ));
  }, [failedAlertsScope, failedAlertGroups, activeFailedAlertGroups, failedAlertsSearch]);

  const filteredLogs = useMemo(() => {
    let rows = operationLogs;

    if (logsStatusFilter !== "all") {
      rows = rows.filter((row) => row.status === logsStatusFilter);
    }

    const search = logsSearch.trim().toLowerCase();
    if (!search) return rows;

    return rows.filter((row) => (
      row.storeName.toLowerCase().includes(search)
      || row.productLabel.toLowerCase().includes(search)
      || (row.errorMessage || "").toLowerCase().includes(search)
      || (row.httpStatusCode !== null && String(row.httpStatusCode).includes(search))
    ));
  }, [operationLogs, logsStatusFilter, logsSearch]);

  const chartConfig = {
    count: { label: "Requests", color: "hsl(var(--cho-teal))" },
  };

  return (
    <div>
      <PageHeader
        icon={Activity}
        title="Pipeline Health & Logs"
        subtitle="Monitor scraping health from raw_staging with success rate, HTTP statuses, and failed request diagnostics."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <MetricCard label="Success Rate" value={`${successRate.toFixed(2)}%`} icon={ShieldCheck} accentColor="teal" />
        <MetricCard label="Total Records" value={totalRecords} icon={Database} accentColor="gold" />
        <div className="glass-card rounded-2xl p-4 border border-destructive/20 bg-destructive/5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold mb-1">Active Alerts</p>
              <p className="text-2xl font-black text-destructive tabular-nums">{activeAlertsCount}</p>
              <p className="text-xs text-muted-foreground mt-1">from {failedRequests} failed rows</p>
            </div>
            <AlertTriangle className="w-5 h-5 text-destructive" />
          </div>
        </div>
      </div>

      <div className="glass-card rounded-2xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm uppercase tracking-wider font-bold text-muted-foreground">HTTP Status Codes</h3>
          <div className="flex items-center gap-2">
            <Badge className="bg-[hsl(var(--cho-teal))/0.12] text-[hsl(var(--cho-teal))] border-[hsl(var(--cho-teal))/0.3]">200 Success</Badge>
            <Badge className="bg-destructive/10 text-destructive border-destructive/20">Errors (404/500)</Badge>
          </div>
        </div>

        {isLoading ? (
          <div className="h-[320px] grid place-items-center text-muted-foreground">Loading status chart...</div>
        ) : (
          <ChartContainer config={chartConfig} className="h-[320px] w-full">
            <BarChart data={statusData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.5} />
              <XAxis dataKey="statusLabel" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                {statusData.map((row, index) => (
                  <Cell key={`${row.statusLabel}-${index}`} fill={row.color} />
                ))}
              </Bar>
            </BarChart>
          </ChartContainer>
        )}
      </div>

      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-border/50 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm uppercase tracking-wider font-bold text-muted-foreground">Failed Requests</h3>
              <Badge className="bg-destructive/10 text-destructive border-destructive/20">
                {activeAlertsCount} active
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {isLoading
                ? "Loading failed alerts..."
                : activeAlertsCount > 0
                  ? `${activeAlertsCount} active alert${activeAlertsCount === 1 ? "" : "s"} need attention.`
                  : failedAlertGroups.length > 0
                    ? "All current alerts are dismissed. They will reappear only if the issue happens again."
                    : "No active scraping alerts."}
            </p>
          </div>

          <div className="flex flex-col md:flex-row gap-2 md:items-center">
            <Button
              variant="outline"
              size="sm"
              className="h-9 rounded-lg"
              onClick={acknowledgeAllActiveAlerts}
              disabled={activeAlertsCount === 0}
            >
              Dismiss all
            </Button>
            <Input
              value={failedAlertsSearch}
              onChange={(event) => setFailedAlertsSearch(event.target.value)}
              placeholder="Search store, product, error, or code..."
              className="h-9 min-w-[240px]"
            />
            <Select value={failedAlertsScope} onValueChange={(value) => setFailedAlertsScope(value as FailedAlertsScope)}>
              <SelectTrigger className="h-9 min-w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active Alerts</SelectItem>
                <SelectItem value="all">All Alert Groups</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider">Store Name</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Error Message</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Last Seen</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-right">Occurrences</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-center">State</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">Loading failed requests...</TableCell>
              </TableRow>
            ) : visibleFailedAlertGroups.length ? (
              visibleFailedAlertGroups.map((group) => {
                const screenshotUrl = resolveStorageUrl(group.latestScreenshotPath);
                const active = isAlertActive(group, alertAcknowledgements);

                return (
                  <TableRow key={group.alertKey} className="hover:bg-muted/20">
                    <TableCell className="text-sm">
                      <div className="font-semibold">{group.storeName}</div>
                      <div className="text-muted-foreground text-xs truncate max-w-[360px]">{group.productLabel}</div>
                    </TableCell>
                    <TableCell className="text-sm text-destructive/90">{group.errorMessage || "No error message"}</TableCell>
                    <TableCell className="text-sm whitespace-nowrap">{new Date(group.lastSeenAt).toLocaleString()}</TableCell>
                    <TableCell className="text-sm text-right font-semibold tabular-nums">{group.occurrenceCount}</TableCell>
                    <TableCell className="text-center">
                      <Badge className={active ? "bg-destructive/10 text-destructive border-destructive/20" : "bg-muted text-muted-foreground border-border"}>
                        {active ? "Active" : "Dismissed"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        {screenshotUrl ? (
                          <Button variant="ghost" size="sm" className="h-8 px-2 rounded-lg" asChild>
                            <a href={screenshotUrl} target="_blank" rel="noopener noreferrer">
                              <Camera className="w-3.5 h-3.5 mr-1" /> View <ExternalLink className="w-3 h-3 ml-1" />
                            </a>
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground">No screenshot</span>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 px-2 rounded-lg"
                          onClick={() => retryMutation.mutate(group.latestRowId)}
                          disabled={retryMutation.isPending}
                        >
                          {retryMutation.isPending && retryRowId === group.latestRowId
                            ? <RotateCw className="w-3.5 h-3.5 mr-1 animate-spin" />
                            : <RefreshCcw className="w-3.5 h-3.5 mr-1" />}
                          Retry
                        </Button>
                        {active ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 px-2 rounded-lg"
                            onClick={() => acknowledgeAlert(group)}
                          >
                            Dismiss
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-8 px-2 rounded-lg"
                            onClick={() => restoreAcknowledgedAlert(group)}
                          >
                            Restore
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">No failed requests found for the selected scope.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <div className="glass-card rounded-2xl overflow-hidden mt-6">
        <div className="p-4 border-b border-border/50 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h3 className="text-sm uppercase tracking-wider font-bold text-muted-foreground">Scraping Operations Log</h3>

          <div className="flex flex-col md:flex-row gap-2 md:items-center">
            <Input
              value={logsSearch}
              onChange={(event) => setLogsSearch(event.target.value)}
              placeholder="Search store, target, error, or code..."
              className="h-9 min-w-[260px]"
            />
            <Select value={logsStatusFilter} onValueChange={(value) => setLogsStatusFilter(value as LogStatusFilter)}>
              <SelectTrigger className="h-9 min-w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="processed">Success</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider">Time</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Target</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Status</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Result</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {logsLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">Loading operation logs...</TableCell>
              </TableRow>
            ) : filteredLogs.length ? (
              filteredLogs.map((row) => {
                const badgeClass =
                  row.status === "processed"
                    ? "bg-[hsl(var(--cho-teal))/0.12] text-[hsl(var(--cho-teal))] border-[hsl(var(--cho-teal))/0.3]"
                    : row.status === "failed"
                      ? "bg-destructive/10 text-destructive border-destructive/20"
                      : "bg-primary/10 text-primary border-primary/30";

                const statusLabel =
                  row.status === "processed"
                    ? "Success"
                    : row.status === "failed"
                      ? "Failed"
                      : "Pending";

                const screenshotUrl = resolveStorageUrl(row.screenshotPath);

                return (
                  <TableRow key={row.rawStagingId} className="hover:bg-muted/20">
                    <TableCell className="text-sm whitespace-nowrap">{new Date(row.scrapedAt).toLocaleString()}</TableCell>
                    <TableCell className="text-sm">
                      <div className="font-semibold">{row.storeName}</div>
                      <div className="text-muted-foreground text-xs truncate max-w-[340px]">{row.productLabel}</div>
                    </TableCell>
                    <TableCell className="text-center">
                      <Badge className={badgeClass}>{statusLabel}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {row.status === "failed" ? (row.errorMessage || "Operation failed") : `HTTP ${row.httpStatusCode ?? "-"}`}
                    </TableCell>
                    <TableCell className="text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        {screenshotUrl ? (
                          <Button variant="ghost" size="sm" className="h-8 px-2 rounded-lg" asChild>
                            <a href={screenshotUrl} target="_blank" rel="noopener noreferrer">
                              <Camera className="w-3.5 h-3.5 mr-1" /> View <ExternalLink className="w-3 h-3 ml-1" />
                            </a>
                          </Button>
                        ) : (
                          <span className="text-xs text-muted-foreground">No screenshot</span>
                        )}

                        {row.status === "failed" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-2 rounded-lg"
                            onClick={() => retryMutation.mutate(row.rawStagingId)}
                            disabled={retryMutation.isPending}
                          >
                            {retryMutation.isPending && retryRowId === row.rawStagingId
                              ? <RotateCw className="w-3.5 h-3.5 mr-1 animate-spin" />
                              : <RefreshCcw className="w-3.5 h-3.5 mr-1" />}
                            Retry
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-muted-foreground">No operation logs found for the selected filters.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
