import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import {
  getRetailPresence,
  getRetailPresenceCountryMetrics,
  RetailPresenceCell,
  RetailPresenceStatus,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { RetailPresenceWorldMap } from "@/components/RetailPresenceWorldMap";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  MapPinned,
  Search,
  LayoutGrid,
  AlertTriangle,
  X,
} from "lucide-react";

const STATUS_LABEL: Record<RetailPresenceStatus, string> = {
  all_present: "All Present",
  partial: "Partial",
  none: "Missing",
};

function getStatusBadgeClass(status: RetailPresenceStatus): string {
  if (status === "all_present") {
    return "bg-[hsl(var(--cho-teal))/0.12] text-[hsl(var(--cho-teal))] border-[hsl(var(--cho-teal))/0.25]";
  }
  if (status === "partial") {
    return "bg-primary/10 text-primary border-primary/30";
  }
  return "bg-destructive/10 text-destructive border-destructive/25";
}

type FlatPresenceRow = {
  productFormatId: number;
  productLabel: string;
  familyLabel: string;
  formatLabel: string;
  presenceStatus: RetailPresenceStatus;
  presentCount: number;
  cells: RetailPresenceCell[];
};

function buildProductLabel(familyLabel: string, formatLabel: string): string {
  const family = familyLabel.trim();
  const format = formatLabel.trim();
  if (!family) return format;
  if (!format) return family;

  if (format.toLowerCase().startsWith(family.toLowerCase())) {
    return format;
  }

  return `${family} ${format}`.trim();
}

export default function RetailPresence() {
  const [selectedCountry, setSelectedCountry] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | RetailPresenceStatus>("all");

  const { data: countryMetrics } = useQuery({
    queryKey: ["retail-presence-country-metrics"],
    queryFn: () => getRetailPresenceCountryMetrics(),
  });

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["retail-presence", selectedCountry || "default"],
    queryFn: () => getRetailPresence(selectedCountry),
  });

  const websites = data?.websites || [];

  const flatRows = useMemo<FlatPresenceRow[]>(() => {
    const rows = data?.rows || [];
    return rows.flatMap((row) =>
      row.formats.map((formatRow) => ({
        productFormatId: formatRow.productFormatId,
        productLabel: buildProductLabel(row.familyLabel, formatRow.formatLabel),
        familyLabel: row.familyLabel,
        formatLabel: formatRow.formatLabel,
        presenceStatus: formatRow.presenceStatus,
        presentCount: formatRow.presentCount,
        cells: formatRow.cells,
      })),
    );
  }, [data?.rows]);

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();

    return flatRows.filter((row) => {
      if (statusFilter !== "all" && row.presenceStatus !== statusFilter) return false;
      if (!q) return true;

      return (
        row.productLabel.toLowerCase().includes(q) ||
        row.familyLabel.toLowerCase().includes(q) ||
        row.formatLabel.toLowerCase().includes(q)
      );
    });
  }, [flatRows, search, statusFilter]);

  const filteredMatrixCells = useMemo(() => {
    return filteredRows.length * websites.length;
  }, [filteredRows, websites.length]);

  const globalPresenceValue = `${(data?.kpis.coverageRate || 0).toFixed(2)}%`;
  const globalSignalValue = `${data?.kpis.presentCells || 0}/${data?.kpis.totalMatrixCells || 0} signals`;
  const actionableGapValue = data?.kpis.missingCells || 0;
  const actionableProducts = flatRows.filter((row) => row.presenceStatus !== "all_present").length;

  return (
    <div>
      <PageHeader
        icon={MapPinned}
        title="Retail Presence"
        subtitle="Map-first retail presence: choose geography first, then review actionable coverage gaps."
      />

      {/* Map Section - Compact */}
      <div className="glass-card rounded-2xl p-3 mb-4">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="h-6 w-1 rounded-full bg-[hsl(var(--cho-teal))]" />
            <div>
              <p className="text-sm font-semibold text-foreground">Geo Scope</p>
              <p className="text-[11px] text-muted-foreground">
                Hover for stats, click to filter • Tracked: <span className="font-semibold text-foreground">{countryMetrics?.length || 0}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {selectedCountry && (
              <div className="flex items-center gap-1.5 rounded-lg border border-[hsl(var(--cho-teal))]/30 bg-[hsl(var(--cho-teal))]/0.06 px-2.5 py-1 text-xs">
                <span className="text-muted-foreground">Filter:</span>
                <span className="font-medium text-[hsl(var(--cho-teal))]">{selectedCountry}</span>
                <button
                  onClick={() => setSelectedCountry(undefined)}
                  className="ml-1 rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setSelectedCountry(undefined)}
              disabled={!selectedCountry}
              className="h-7 rounded-lg text-xs"
            >
              <X className="w-3 h-3 mr-1" /> Clear
            </Button>
          </div>
        </div>

        <div className="rounded-xl border border-border/50 gradient-mesh p-2">
          <RetailPresenceWorldMap
            metrics={countryMetrics || []}
            selectedCountry={selectedCountry}
            onSelectCountry={setSelectedCountry}
            className="rounded-lg border border-border/50 bg-background/70"
          />
          <p className="mt-1.5 text-[11px] text-muted-foreground">
            Only countries with tracked websites are clickable.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-border/60 bg-background/80 px-4 py-3 transition-shadow hover:shadow-sm border-l-[3px] border-l-[hsl(var(--cho-teal))] bg-gradient-to-r from-[hsl(var(--cho-teal)/0.06)] to-background/80">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[hsl(var(--cho-teal))]">Global Presence</p>
              <p className="mt-1.5 text-2xl font-bold text-foreground tabular-nums leading-none tracking-tight">{globalPresenceValue}</p>
              <p className="mt-1 text-[11px] text-muted-foreground">{globalSignalValue}</p>
            </div>
            <LayoutGrid className="h-8 w-8 text-[hsl(var(--cho-teal))]/20" />
          </div>
        </div>
        <div className="rounded-xl border border-border/60 bg-background/80 px-4 py-3 transition-shadow hover:shadow-sm border-l-[3px] border-l-[hsl(var(--cho-gold))] bg-gradient-to-r from-[hsl(var(--cho-gold)/0.06)] to-background/80">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[hsl(var(--cho-gold-dark))]">Actionable Gaps</p>
              <p className="mt-1.5 text-2xl font-bold text-foreground tabular-nums leading-none tracking-tight">{actionableGapValue}</p>
              <p className="mt-1 text-[11px] text-muted-foreground">{actionableProducts} products need attention</p>
            </div>
            <AlertTriangle className="h-8 w-8 text-[hsl(var(--cho-gold))]/20" />
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="glass-card rounded-2xl p-3 mb-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[hsl(var(--cho-gold))]" />
            <p className="text-xs font-semibold text-foreground">Presence Matrix</p>
          </div>
          <div className="mx-2 h-4 w-px bg-border/50" />
          <div className="relative flex-1 min-w-[200px] max-w-[300px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search product..."
              className="pl-9 h-8 rounded-lg text-xs bg-background/65 border-border/55"
            />
          </div>
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as "all" | RetailPresenceStatus)}>
            <SelectTrigger className="h-8 w-[150px] rounded-lg text-xs bg-background/65 border-border/55">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="all_present">All Present</SelectItem>
              <SelectItem value="partial">Partial</SelectItem>
              <SelectItem value="none">Missing</SelectItem>
            </SelectContent>
          </Select>
          <p className="text-[11px] text-muted-foreground ml-auto">
            {filteredRows.length} products • {websites.length} stores
          </p>
        </div>
      </div>

      {/* Presence Matrix Table */}
      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="px-4 py-2.5 border-b border-border/50 flex items-center justify-between bg-muted/20">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[hsl(var(--cho-teal))]" />
            <h3 className="text-xs font-semibold text-foreground">Product Availability</h3>
          </div>
          <p className="text-[11px] text-muted-foreground">
            {filteredMatrixCells} cells {isFetching ? "• refreshing" : ""}
          </p>
        </div>

        <Table className="min-w-[880px]">
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider w-[360px]">Product</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-center w-[170px]">Availability</TableHead>
              {websites.map((website) => (
                <TableHead key={website.websiteId} className="font-bold text-xs uppercase tracking-wider text-center min-w-[110px]">
                  <div className="leading-tight">
                    <p>{website.siteName}</p>
                    <p className="text-[10px] text-muted-foreground normal-case mt-0.5">{website.country || "-"}</p>
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>

          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={2 + Math.max(1, websites.length)} className="py-10 text-center text-muted-foreground">
                  Loading retail presence matrix...
                </TableCell>
              </TableRow>
            ) : filteredRows.length ? (
              filteredRows.map((row) => (
                <TableRow key={`format-${row.productFormatId}`} className="hover:bg-background/60">
                  <TableCell>
                    <div className="font-medium text-sm">{row.productLabel}</div>
                    <div className="text-xs text-muted-foreground">
                      {row.familyLabel}
                    </div>
                  </TableCell>

                  <TableCell className="text-center">
                    <div className="flex flex-col items-center gap-1">
                      <Badge className={cn("rounded-full", getStatusBadgeClass(row.presenceStatus))}>
                        {STATUS_LABEL[row.presenceStatus]}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {row.presentCount}/{websites.length} stores
                      </span>
                    </div>
                  </TableCell>

                  {websites.map((website) => {
                    const cell = row.cells.find((rowCell) => rowCell.websiteId === website.websiteId);
                    return (
                      <TableCell key={`cell-${row.productFormatId}-${website.websiteId}`} className="text-center">
                        {cell?.present ? (
                          <Badge className="rounded-full bg-[hsl(var(--cho-teal))/0.14] text-[hsl(var(--cho-teal))] border-[hsl(var(--cho-teal))/0.35]">
                            Exists
                          </Badge>
                        ) : (
                          <Badge className="rounded-full bg-destructive/10 text-destructive border-destructive/30">
                            Not Found
                          </Badge>
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={2 + Math.max(1, websites.length)} className="py-10 text-center text-muted-foreground">
                  No products match your filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}