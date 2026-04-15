import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import { getOperationalVisibility, resolveStorageUrl } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { BarChart, Bar, CartesianGrid, XAxis, YAxis, Cell } from "recharts";
import { ShieldCheck, Database, AlertTriangle, Activity, Camera, ExternalLink } from "lucide-react";

export default function OperationalVisibility() {
  const { data, isLoading } = useQuery({
    queryKey: ["operational-visibility"],
    queryFn: () => getOperationalVisibility(200),
  });

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

  const chartConfig = {
    count: { label: "Requests", color: "hsl(var(--cho-teal))" },
  };

  return (
    <div>
      <PageHeader
        icon={Activity}
        title="Operational Visibility"
        subtitle="Monitor scraping health from raw_staging with success rate, HTTP statuses, and failed request diagnostics."
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <MetricCard label="Success Rate" value={`${successRate.toFixed(2)}%`} icon={ShieldCheck} accentColor="teal" />
        <MetricCard label="Total Records" value={totalRecords} icon={Database} accentColor="gold" />
        <div className="glass-card rounded-2xl p-4 border border-destructive/20 bg-destructive/5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold mb-1">Failed Requests</p>
              <p className="text-2xl font-black text-destructive tabular-nums">{failedRequests}</p>
              <p className="text-xs text-muted-foreground mt-1">status = failed</p>
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
        <div className="p-4 border-b border-border/50">
          <h3 className="text-sm uppercase tracking-wider font-bold text-muted-foreground">Failed Requests</h3>
        </div>
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider">Store Name</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Error Message</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Screenshot</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={3} className="py-10 text-center text-muted-foreground">Loading failed requests...</TableCell>
              </TableRow>
            ) : data?.failedRows?.length ? (
              data.failedRows.map((row) => {
                const screenshotUrl = resolveStorageUrl(row.screenshotPath);
                return (
                  <TableRow key={row.id} className="hover:bg-muted/20">
                    <TableCell className="font-semibold text-sm">{row.storeName}</TableCell>
                    <TableCell className="text-sm text-destructive/90">{row.errorMessage || "No error message"}</TableCell>
                    <TableCell className="text-center">
                      {screenshotUrl ? (
                        <Button variant="ghost" size="sm" className="h-8 px-2 rounded-lg" asChild>
                          <a href={screenshotUrl} target="_blank" rel="noopener noreferrer">
                            <Camera className="w-3.5 h-3.5 mr-1" /> View <ExternalLink className="w-3 h-3 ml-1" />
                          </a>
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={3} className="py-10 text-center text-muted-foreground">No failed requests found.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
