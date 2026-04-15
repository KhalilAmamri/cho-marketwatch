import { useEffect, useMemo, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import {
  getRetailPresence,
  RetailPresenceCell,
  RetailPresenceStatus,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  MapPinned,
  Search,
  LayoutGrid,
  AlertTriangle,
} from "lucide-react";

const STATUS_LABEL: Record<RetailPresenceStatus, string> = {
  all_present: "All Present",
  partial: "Partial",
  none: "Missing",
};

const GEO_COUNTRIES = [
  {
    key: "sweden",
    label: "Sweden",
    isoCode: "SE",
    tooltipSide: "right",
    // Simplified from real-world boundaries (WGS84), projected and fitted to this viewBox.
    path: "M140.50,67.84 L129.33,75.72 L131.13,82.47 L90.56,100.08 L82.17,114.22 L101.39,126.33 L90.81,136.80 L78.83,138.93 L74.43,153.79 L67.89,161.79 L53.92,160.98 L47.40,167.62 L34.06,168.00 L30.40,160.08 L12.00,137.69 L26.66,125.99 L30.47,114.68 L23.11,109.68 L22.40,96.16 L29.88,86.23 L41.31,86.41 L45.32,82.12 L41.12,78.37 L59.01,62.40 L78.13,40.38 L89.20,40.42 L92.24,33.34 L113.95,35.39 L115.64,26.85 L122.79,26.31 L156.12,41.36 L156.43,60.04 L160.31,64.58 Z M81.51,150.79 L83.22,151.31 L74.23,161.16 L73.47,157.95 Z M107.96,145.75 L96.00,154.77 L93.53,155.09 L94.48,153.20 L93.15,151.83 L94.10,150.72 L93.40,149.40 L108.15,145.42 Z M125.10,88.83 L126.56,89.98 L123.36,91.30 L124.56,89.29 Z",
    labelX: 84,
    labelY: 98,
  },
  {
    key: "finland",
    label: "Finland",
    isoCode: "FI",
    tooltipSide: "left",
    path: "M214.32,26.86 L212.64,35.94 L230.28,44.32 L219.65,53.52 L233.04,66.89 L225.29,76.58 L235.66,84.74 L230.95,91.70 L248.00,98.86 L243.67,104.07 L208.31,122.33 L148.41,128.55 L130.58,120.25 L133.15,110.62 L127.55,101.53 L143.49,88.89 L177.53,74.76 L176.33,70.00 L160.31,64.58 L156.43,60.04 L156.12,41.36 L122.79,26.31 L129.69,22.80 L142.49,29.78 L169.90,32.28 L180.88,26.50 L186.53,16.66 L204.42,12.00 L219.20,17.46 Z",
    labelX: 196,
    labelY: 88,
  },
] as const;

function normalizeCountryKey(country?: string): string {
  return String(country || "").trim().toLowerCase();
}

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

function CountrySelectorMap({
  countries,
  countryRetailers,
  selectedCountry,
  onSelect,
}: {
  countries: string[];
  countryRetailers: Record<string, string[]>;
  selectedCountry?: string;
  onSelect: (country: string) => void;
}) {
  const [tooltip, setTooltip] = useState<{ countryKey: string; xPct: number; yPct: number } | null>(null);
  const selectedKey = normalizeCountryKey(selectedCountry);
  const countryMap = new Map(countries.map((country) => [normalizeCountryKey(country), country]));
  const unsupportedCountries = countries.filter(
    (country) => !GEO_COUNTRIES.some((geoCountry) => geoCountry.key === normalizeCountryKey(country)),
  );
  const retailersByCountryKey = useMemo(() => {
    const grouped = new Map<string, string[]>();

    for (const [country, retailers] of Object.entries(countryRetailers || {})) {
      grouped.set(normalizeCountryKey(country), retailers || []);
    }

    return grouped;
  }, [countryRetailers]);
  const hoveredCountry = tooltip ? GEO_COUNTRIES.find((country) => country.key === tooltip.countryKey) : undefined;
  const hoveredRetailers = tooltip ? (retailersByCountryKey.get(tooltip.countryKey) || []) : [];

  function updateTooltipFromEvent(event: ReactMouseEvent<SVGGElement>, countryKey: string) {
    const svg = event.currentTarget.ownerSVGElement;
    if (!svg) return;

    const rect = svg.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const xPct = ((event.clientX - rect.left) / rect.width) * 100;
    const yPct = ((event.clientY - rect.top) / rect.height) * 100;
    setTooltip({
      countryKey,
      xPct: Math.max(8, Math.min(92, xPct)),
      yPct: Math.max(8, Math.min(92, yPct)),
    });
  }

  return (
    <div className="glass-card rounded-2xl p-4 mb-6">
      <div className="flex flex-col gap-1 mb-3">
        <p className="text-[10px] uppercase tracking-[0.15em] font-bold text-muted-foreground">Geo Scope</p>
        <p className="text-sm text-muted-foreground">Click Sweden or Finland on the mini-map to filter the matrix instantly. Hover to preview retailers.</p>
      </div>

      <div className="rounded-2xl border border-border/50 gradient-mesh p-4">
        <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-4 items-start">
          <div className="relative rounded-xl border border-border/50 bg-background/70 p-3">
            <svg viewBox="0 0 260 180" className="w-full h-[190px]" onMouseLeave={() => setTooltip(null)}>
              <rect x="0" y="0" width="260" height="180" rx="16" fill="hsl(var(--background))" opacity="0.45" />
              {GEO_COUNTRIES.map((geoCountry) => {
                const country = countryMap.get(geoCountry.key);
                const isAvailable = Boolean(country);
                const isSelected = selectedKey === geoCountry.key;

                return (
                  <g
                    key={geoCountry.key}
                    className={cn(isAvailable && "cursor-pointer")}
                    onMouseEnter={(event) => {
                      if (!isAvailable) return;
                      updateTooltipFromEvent(event, geoCountry.key);
                    }}
                    onMouseMove={(event) => {
                      if (!isAvailable) return;
                      updateTooltipFromEvent(event, geoCountry.key);
                    }}
                    onMouseLeave={() => setTooltip((prev) => (prev?.countryKey === geoCountry.key ? null : prev))}
                    onClick={() => {
                      if (country) onSelect(country);
                    }}
                  >
                    <path
                      d={geoCountry.path}
                      className={cn(
                        "transition-colors",
                        isSelected
                          ? "fill-accent/75 stroke-accent"
                          : isAvailable
                            ? "fill-primary/20 stroke-primary/60 hover:fill-primary/35"
                            : "fill-muted/40 stroke-muted-foreground/30",
                      )}
                      strokeWidth="1.5"
                    />
                    <text
                      x={geoCountry.labelX}
                      y={geoCountry.labelY}
                      textAnchor="middle"
                      className={cn(
                        "text-[10px] font-semibold select-none",
                        isSelected
                          ? "fill-accent-foreground"
                          : isAvailable
                            ? "fill-foreground"
                            : "fill-muted-foreground",
                      )}
                    >
                      {geoCountry.label}
                    </text>
                  </g>
                );
              })}
            </svg>

            {tooltip && hoveredCountry && (
              <div
                className="absolute z-20 pointer-events-none rounded-lg border border-border/60 bg-background/95 px-3 py-2 shadow-xl w-[220px]"
                style={{
                  left: `${tooltip.xPct}%`,
                  top: `${tooltip.yPct}%`,
                  transform:
                    hoveredCountry.tooltipSide === "left"
                      ? "translate(calc(-100% - 12px), -50%)"
                      : "translate(12px, -50%)",
                }}
              >
                <p className="text-xs font-semibold text-foreground">
                  {hoveredCountry.label} ({hoveredCountry.isoCode})
                </p>
                <p className="text-[10px] uppercase tracking-[0.12em] font-semibold text-muted-foreground mt-1">Retailers</p>
                <p className="text-xs text-foreground mt-0.5 leading-relaxed">
                  {hoveredRetailers.length ? hoveredRetailers.join(", ") : "No retailers linked"}
                </p>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              Current filter: <span className="font-semibold text-foreground">{selectedCountry || "Not selected"}</span>
            </p>
            <div className="flex flex-wrap gap-2">
              {GEO_COUNTRIES.map((geoCountry) => {
                const isAvailable = countryMap.has(geoCountry.key);
                const isSelected = selectedKey === geoCountry.key;
                return (
                  <Badge
                    key={geoCountry.key}
                    variant="outline"
                    className={cn(
                      "rounded-full",
                      isSelected && "border-primary text-primary bg-primary/10",
                      !isAvailable && "opacity-50",
                    )}
                  >
                    {geoCountry.label}
                  </Badge>
                );
              })}
            </div>

            {unsupportedCountries.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Other countries in dataset: {unsupportedCountries.join(", ")}.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


export default function RetailPresence() {
  const [selectedCountry, setSelectedCountry] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | RetailPresenceStatus>("all");

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["retail-presence", selectedCountry || "default"],
    queryFn: () => getRetailPresence(selectedCountry),
  });

  useEffect(() => {
    if (!selectedCountry && data?.country) {
      setSelectedCountry(data.country);
    }
  }, [data?.country, selectedCountry]);

  const rows = data?.rows || [];
  const websites = data?.websites || [];

  const flatRows = useMemo<FlatPresenceRow[]>(() => {
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
  }, [rows]);

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

      <CountrySelectorMap
        countries={data?.availableCountries || []}
        countryRetailers={data?.countryRetailers || {}}
        selectedCountry={selectedCountry}
        onSelect={setSelectedCountry}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <MetricCard
          label="Global Presence"
          value={globalPresenceValue}
          icon={LayoutGrid}
          accentColor="teal"
          trend="neutral"
          trendValue={globalSignalValue}
        />
        <MetricCard
          label="Actionable Gaps"
          value={actionableGapValue}
          icon={AlertTriangle}
          accentColor="gold"
          trend="neutral"
          trendValue={`${actionableProducts} products need attention`}
        />
      </div>

      <div className="glass-card rounded-2xl p-4 mb-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-center">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search product name"
              className="pl-10 h-10 rounded-xl bg-background/60 border-border/50"
            />
          </div>

          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as "all" | RetailPresenceStatus)}>
            <SelectTrigger className="h-10 rounded-xl bg-background/60 border-border/50">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="all_present">All Present</SelectItem>
              <SelectItem value="partial">Partial</SelectItem>
              <SelectItem value="none">Missing</SelectItem>
            </SelectContent>
          </Select>

          <div className="text-xs text-muted-foreground md:text-right">
            One row = one product format. Columns show if each store has that exact product.
          </div>
        </div>
      </div>

      <div className="glass-card rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-border/50 flex items-center justify-between">
          <h3 className="text-sm uppercase tracking-wider font-bold text-muted-foreground">Presence Matrix</h3>
          <p className="text-xs text-muted-foreground">
            {filteredRows.length} products • {websites.length} stores • {filteredMatrixCells} matrix cells {isFetching ? "• refreshing" : ""}
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