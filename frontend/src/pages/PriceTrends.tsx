import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  LabelList,
  Line,
  LineChart,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from "recharts";

import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import {
  getFilters,
  getAvailableWeeks,
  getMarketChanges,
  getMarketOverview,
  getPriceAnalysis,
  getSummary,
  getStoreUniverse,
  getTimeseries,
  resolveStorageUrl,
  type MarketChangeRow,
  type StorePresenceSlice,
  type StoreOption,
  type TimeseriesRow,
} from "@/lib/api";

function uniqueSorted(values: string[]): string[] {
  return [...new Set(values.filter((value) => Boolean(value && value.trim())))].sort((a, b) =>
    a.localeCompare(b),
  );
}

function formatNumber(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `${value.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

function formatAxisNumber(value: number): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "";
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatWeekLabel(weekStart: string): string {
  try {
    const date = new Date(`${weekStart}T00:00:00Z`);
    if (Number.isNaN(date.getTime())) return weekStart;
    const parts = new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    }).formatToParts(date);
    const day = parts.find((p) => p.type === "day")?.value;
    const month = parts.find((p) => p.type === "month")?.value;
    const year = parts.find((p) => p.type === "year")?.value;
    if (!day || !month || !year) return weekStart;
    return `${day} ${month}, ${year}`;
  } catch {
    return weekStart;
  }
}

function computePaddedDomain(values: number[]): { min: number; max: number } | null {
  const numeric = values.filter((v) => typeof v === "number" && Number.isFinite(v));
  if (!numeric.length) return null;

  const dataMin = Math.min(...numeric);
  const dataMax = Math.max(...numeric);
  const span = dataMax - dataMin;
  const pad = span > 0 ? span * 0.08 : Math.max(Math.abs(dataMin) * 0.04, 0.5);
  return {
    min: dataMin - pad,
    max: dataMax + pad,
  };
}

function formatStoreLabel(store: string, country?: string | null): string {
  const fallbackCountries: Record<string, string> = {
    citygross: "sweden",
    coop: "sweden",
    ica: "sweden",
    kesko: "finland",
    sok: "finland",
  };
  const storeLabel = store.trim().toLowerCase();
  const resolvedCountry = (country?.trim().toLowerCase() || fallbackCountries[storeLabel] || "").trim();
  if (!resolvedCountry) return storeLabel;
  return `${storeLabel}-${resolvedCountry}`;
}

function toIsoDateString(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function buildWeeklyAxis(weeks: string[]): string[] {
  const sorted = [...new Set(weeks.filter(Boolean))].sort((a, b) => a.localeCompare(b));
  if (!sorted.length) return [];

  // If the dataset contains mixed week_start conventions (e.g., some Sundays and some Mondays),
  // generating an axis by stepping +7 days from the first point will silently drop the other
  // weekday series. In that case, use the real keys as-is.
  if (sorted.length > 1) {
    const weekdays = new Set<number>();
    for (const value of sorted) {
      const d = new Date(`${value}T00:00:00Z`);
      if (Number.isNaN(d.getTime())) continue;
      weekdays.add(d.getUTCDay());
      if (weekdays.size > 1) return sorted;
    }
  }

  const start = new Date(`${sorted[0]}T00:00:00Z`);
  const end = new Date(`${sorted[sorted.length - 1]}T00:00:00Z`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return sorted;

  const axis: string[] = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    axis.push(toIsoDateString(cursor));
    cursor.setUTCDate(cursor.getUTCDate() + 7);
  }
  return axis;
}

function KpiCard(props: { label: string; value: ReactNode; className?: string; accent?: "teal" | "gold" | "none" }) {
  const accentColor = props.accent || "none";
  const accentClasses = {
    teal: "border-l-[3px] border-l-[hsl(var(--cho-teal))] bg-gradient-to-r from-[hsl(var(--cho-teal)/0.06)] to-background/80",
    gold: "border-l-[3px] border-l-[hsl(var(--cho-gold))] bg-gradient-to-r from-[hsl(var(--cho-gold)/0.06)] to-background/80",
    none: "",
  };

  const labelClasses = {
    teal: "text-[hsl(var(--cho-teal))]",
    gold: "text-[hsl(var(--cho-gold-dark))]",
    none: "text-muted-foreground/90",
  };

  return (
    <div className={cn(
      "rounded-xl border border-border/60 bg-background/80 px-3 py-2.5 transition-shadow hover:shadow-sm",
      accentClasses[accentColor],
      props.className
    )}>
      <p className={cn("text-[10px] font-bold uppercase tracking-[0.12em]", labelClasses[accentColor])}>
        {props.label}
      </p>
      <div className="mt-1.5 min-h-[2.25rem]">
        {typeof props.value === "string" || typeof props.value === "number" ? (
          <p className="text-lg font-bold text-foreground tabular-nums leading-none tracking-tight">
            {props.value}
          </p>
        ) : (
          props.value
        )}
      </div>
    </div>
  );
}

const OTHERS_COLOR = "hsl(var(--muted-foreground))";

// Use only theme tokens (no hard-coded colors).
// Keep a stable palette for multi-series charts (e.g., deep trend lines).
const PIE_COLORS = [
  "hsl(var(--cho-teal))",
  "hsl(var(--cho-gold))",
  "hsl(var(--cho-teal-light))",
  "hsl(var(--cho-gold-light))",
  "hsl(var(--cho-gold-dark))",
  "hsl(var(--muted-foreground))",
];

// Dedicated, clearly distinct palette for the Market Overview distribution pie.
const PRESENCE_SLICE_COLORS = [
  "hsl(var(--cho-gold))",
  "hsl(var(--cho-teal))",
  "hsl(var(--cho-gold-light))",
  "hsl(var(--cho-teal-light))",
];

export default function PriceTrends() {
  const { data: filters } = useQuery({ queryKey: ["filters"], queryFn: getFilters });

  const productOptions = filters?.products || [];

  // ------------------------------
  // Section A: Market overview
  // ------------------------------
  const [marketCountry, setMarketCountry] = useState("all");
  const [marketStore, setMarketStore] = useState("all");
  const [marketWeekStart, setMarketWeekStart] = useState("");
  const [marketChangesOpen, setMarketChangesOpen] = useState(false);

  const marketCountryFilter = marketCountry === "all" ? undefined : marketCountry;
  const marketStoreFilter = marketStore === "all" ? undefined : marketStore;

  const { data: marketWeeks = [] } = useQuery({
    queryKey: ["prices-weeks", marketCountryFilter || "all", marketStoreFilter || "all"],
    queryFn: () =>
      getAvailableWeeks({
        country: marketCountryFilter,
        store: marketStoreFilter,
        limit: 5200,
      }),
  });

  useEffect(() => {
    if (!marketWeeks.length) return;
    if (!marketWeekStart || !marketWeeks.includes(marketWeekStart)) {
      setMarketWeekStart(marketWeeks[0]);
    }
  }, [marketWeeks, marketWeekStart]);

  const { data: marketOverview } = useQuery({
    queryKey: [
      "prices-market-overview",
      marketCountryFilter || "all",
      marketStoreFilter || "all",
      marketWeekStart || "none",
      `fx:${marketWeekStart || "none"}`,
    ],
    queryFn: () =>
      getMarketOverview({
        country: marketCountryFilter,
        store: marketStoreFilter,
        weekStart: marketWeekStart || undefined,
        fxBasisWeekStart: marketWeekStart || undefined,
      }),
    enabled: Boolean(marketWeekStart),
  });

  const marketPreviousWeekStart = useMemo(() => {
    if (!marketWeekStart) return null;
    const index = marketWeeks.indexOf(marketWeekStart);
    if (index < 0) return null;

    const current = new Date(`${marketWeekStart}T00:00:00Z`);
    const currentTime = current.getTime();
    if (Number.isNaN(currentTime)) return marketWeeks[index + 1] || null;

    // Skip near-duplicate week starts that are within the same week window
    // (can happen when the dataset mixes Sunday vs Monday conventions).
    for (let i = index + 1; i < marketWeeks.length; i += 1) {
      const candidate = marketWeeks[i];
      const d = new Date(`${candidate}T00:00:00Z`);
      const t = d.getTime();
      if (Number.isNaN(t)) continue;
      const diffDays = (currentTime - t) / (1000 * 60 * 60 * 24);
      if (diffDays >= 6) return candidate;
    }

    return marketWeeks[index + 1] || null;
  }, [marketWeeks, marketWeekStart]);

  const { data: marketOverviewPrev } = useQuery({
    queryKey: [
      "prices-market-overview-prev",
      marketCountryFilter || "all",
      marketStoreFilter || "all",
      marketPreviousWeekStart || "none",
      `fx:${marketWeekStart || "none"}`,
    ],
    queryFn: () =>
      getMarketOverview({
        country: marketCountryFilter,
        store: marketStoreFilter,
        weekStart: marketPreviousWeekStart || undefined,
        fxBasisWeekStart: marketWeekStart || undefined,
      }),
    enabled: Boolean(marketPreviousWeekStart),
  });

  const marketAvgWoW = useMemo(() => {
    const current = marketOverview?.kpis?.avgUnitPriceEur;
    const previous = marketOverviewPrev?.kpis?.avgUnitPriceEur;
    if (typeof current !== "number" || !Number.isFinite(current)) return null;
    if (typeof previous !== "number" || !Number.isFinite(previous)) return null;
    if (previous <= 0) return null;

    const pct = ((current - previous) / previous) * 100;
    if (!Number.isFinite(pct)) return null;
    const rounded = +pct.toFixed(1);
    return {
      pct: rounded,
      direction: rounded > 0 ? "up" : rounded < 0 ? "down" : "flat",
    } as const;
  }, [marketOverview?.kpis?.avgUnitPriceEur, marketOverviewPrev?.kpis?.avgUnitPriceEur]);

  const { data: marketChanges = [], isFetching: marketChangesLoading } = useQuery({
    queryKey: [
      "prices-market-changes",
      marketCountryFilter || "all",
      marketStoreFilter || "all",
      marketWeekStart || "none",
      marketPreviousWeekStart || "none",
      `fx:${marketWeekStart || "none"}`,
      `open:${marketChangesOpen ? "1" : "0"}`,
    ],
    queryFn: () =>
      getMarketChanges({
        country: marketCountryFilter,
        store: marketStoreFilter,
        weekStart: marketWeekStart,
        previousWeekStart: marketPreviousWeekStart || undefined,
        fxBasisWeekStart: marketWeekStart || undefined,
        limit: 15,
      }),
    enabled: marketChangesOpen && Boolean(marketWeekStart) && Boolean(marketPreviousWeekStart),
  });

  const marketChangesRows = marketChanges as MarketChangeRow[];

  const marketStoreOptions = useMemo(() => {
    const stores = [
      ...(marketOverview?.storeRankings || []).map((row) => row.store),
      ...(marketOverview?.storePresence || []).map((row) => row.store),
    ];
    return uniqueSorted(stores);
  }, [marketOverview?.storeRankings, marketOverview?.storePresence]);

  const marketStoreCountryMap = useMemo(() => {
    const map: Record<string, string | undefined> = {};
    (marketOverview?.storeRankings || []).forEach((row) => {
      map[row.store] = row.country || undefined;
    });
    (marketOverview?.storePresence || []).forEach((row) => {
      map[row.store] = row.country || map[row.store];
    });
    return map;
  }, [marketOverview?.storeRankings, marketOverview?.storePresence]);

  const marketRankingsData = useMemo(
    () =>
      (marketOverview?.storeRankings || [])
        .filter((row) => typeof row.avgUnitPriceEur === "number")
        .map((row) => ({
          store: row.store,
          value: row.avgUnitPriceEur,
        })),
    [marketOverview?.storeRankings],
  );

  const marketPresenceData = useMemo(
    () => (marketOverview?.storePresence || []) as StorePresenceSlice[],
    [marketOverview?.storePresence],
  );

  const marketPresenceChartData = useMemo(() => {
    const mapped = marketPresenceData
      .map((row) => ({
        name: formatStoreLabel(row.store, row.country || marketStoreCountryMap[row.store]),
        value: row.records,
      }))
      .filter((row) => typeof row.value === "number" && Number.isFinite(row.value) && row.value > 0)
      .sort((a, b) => b.value - a.value);

    const top = mapped.slice(0, 4);
    const othersTotal = mapped.slice(4).reduce((sum, row) => sum + row.value, 0);
    if (othersTotal > 0) {
      top.push({ name: "Others", value: othersTotal });
    }
    return top;
  }, [marketPresenceData, marketStoreCountryMap]);

  const marketPresenceTotal = useMemo(
    () => marketPresenceChartData.reduce((sum, row) => sum + row.value, 0),
    [marketPresenceChartData],
  );

  // ------------------------------
  // Section B: Product deep dive
  // ------------------------------
  const [deepProductVariantId, setDeepProductVariantId] = useState("");
  const [deepCountry, setDeepCountry] = useState("all");
  const [deepStore, setDeepStore] = useState("all");
  const [deepWeekStart, setDeepWeekStart] = useState<string>("");
  const [deepTrendWeeks, setDeepTrendWeeks] = useState<number>(52);

  useEffect(() => {
    if (deepProductVariantId) return;
    if (!productOptions.length) return;
    setDeepProductVariantId(String(productOptions[0].productVariantId));
  }, [deepProductVariantId, productOptions]);

  const deepPid = Number(deepProductVariantId);
  const deepCountryFilter = deepCountry === "all" ? undefined : deepCountry;
  const deepStoreFilter = deepStore === "all" ? undefined : deepStore;

  const { data: deepAnalysis } = useQuery({
    queryKey: ["prices-analysis", Number.isFinite(deepPid) ? deepPid : "none", deepCountryFilter || "all"],
    queryFn: () =>
      getPriceAnalysis({
        productVariantIds: [deepPid],
        country: deepCountryFilter,
        weeks: 52,
      }),
    enabled: Number.isFinite(deepPid) && deepPid > 0,
  });

  const deepStoreOptions = useMemo(
    () => uniqueSorted((deepAnalysis?.storeShare || []).map((row) => row.store)),
    [deepAnalysis?.storeShare],
  );

  const deepStoreCountryMap = useMemo(() => {
    const map: Record<string, string | undefined> = {};
    (deepAnalysis?.storeShare || []).forEach((row) => {
      map[row.store] = row.country || undefined;
    });
    return map;
  }, [deepAnalysis?.storeShare]);

  const deepLatestWeekStart = deepAnalysis?.kpis.latestWeekStart || null;

  const { data: deepWeekTimeseries = [] } = useQuery({
    queryKey: [
      "prices-timeseries-week-options",
      Number.isFinite(deepPid) ? deepPid : "none",
      deepCountryFilter || "all",
      deepStoreFilter || "all",
    ],
    queryFn: () => getTimeseries(deepPid, undefined, deepCountryFilter, 0, deepStoreFilter),
    enabled: Number.isFinite(deepPid) && deepPid > 0,
  });

  const deepWeekOptions = useMemo(() => {
    const unique = Array.from(new Set((deepWeekTimeseries || []).map((row) => row.weekStart).filter(Boolean)));
    unique.sort((a, b) => b.localeCompare(a));
    return unique;
  }, [deepWeekTimeseries]);

  const deepPreviousWeekStart = useMemo(() => {
    if (!deepWeekStart) return null;
    const index = deepWeekOptions.indexOf(deepWeekStart);
    if (index < 0) return null;

    const current = new Date(`${deepWeekStart}T00:00:00Z`);
    const currentTime = current.getTime();
    if (Number.isNaN(currentTime)) return deepWeekOptions[index + 1] || null;

    for (let i = index + 1; i < deepWeekOptions.length; i += 1) {
      const candidate = deepWeekOptions[i];
      const d = new Date(`${candidate}T00:00:00Z`);
      const t = d.getTime();
      if (Number.isNaN(t)) continue;
      const diffDays = (currentTime - t) / (1000 * 60 * 60 * 24);
      if (diffDays >= 6) return candidate;
    }

    return deepWeekOptions[index + 1] || null;
  }, [deepWeekOptions, deepWeekStart]);

  const { data: deepStoreUniverse = [] } = useQuery({
    queryKey: ["prices-store-universe", deepCountryFilter || "all"],
    queryFn: () => getStoreUniverse({ country: deepCountryFilter }),
  });

  const deepStoreUniverseMap = useMemo(() => {
    const map: Record<string, string | null> = {};
    (deepStoreUniverse || []).forEach((row: StoreOption) => {
      map[row.store] = row.country ?? null;
    });
    return map;
  }, [deepStoreUniverse]);

  useEffect(() => {
    if (!deepWeekOptions.length) return;
    if (deepWeekStart && deepWeekOptions.includes(deepWeekStart)) return;

    const preferred =
      deepLatestWeekStart && deepWeekOptions.includes(deepLatestWeekStart)
        ? deepLatestWeekStart
        : deepWeekOptions[0];
    setDeepWeekStart(preferred);
  }, [deepWeekOptions, deepWeekStart, deepLatestWeekStart]);

  const { data: deepWeeklySummaryRows } = useQuery({
    queryKey: [
      "prices-summary-weekly",
      Number.isFinite(deepPid) ? deepPid : "none",
      deepWeekStart || "none",
      deepCountryFilter || "all",
      deepStoreFilter || "all",
      `fx:${deepWeekStart || "none"}`,
    ],
    queryFn: () => getSummary(deepWeekStart || undefined, false, "average", deepPid, deepWeekStart || undefined),
    enabled: Number.isFinite(deepPid) && deepPid > 0 && Boolean(deepWeekStart),
  });

  const { data: deepPreviousWeeklySummaryRows } = useQuery({
    queryKey: [
      "prices-summary-weekly-prev",
      Number.isFinite(deepPid) ? deepPid : "none",
      deepPreviousWeekStart || "none",
      deepCountryFilter || "all",
      deepStoreFilter || "all",
      `fx:${deepWeekStart || "none"}`,
    ],
    queryFn: () =>
      getSummary(
        deepPreviousWeekStart || undefined,
        false,
        "average",
        deepPid,
        deepWeekStart || undefined,
      ),
    enabled: Number.isFinite(deepPid) && deepPid > 0 && Boolean(deepPreviousWeekStart),
  });

  const { data: deepLastScrapedRows } = useQuery({
    queryKey: [
      "prices-summary-last-scraped",
      Number.isFinite(deepPid) ? deepPid : "none",
      deepWeekStart || "none",
      deepCountryFilter || "all",
      deepStoreFilter || "all",
    ],
    queryFn: () => getSummary(deepWeekStart || undefined, false, "last_scraped", deepPid),
    enabled: Number.isFinite(deepPid) && deepPid > 0 && Boolean(deepWeekStart),
  });

  const deepWeeklyScopedRows = useMemo(() => {
    const rows = deepWeeklySummaryRows || [];
    return rows
      .filter((row) => (deepCountryFilter ? row.country === deepCountryFilter : true))
      .filter((row) => (deepStoreFilter ? row.store === deepStoreFilter : true));
  }, [deepWeeklySummaryRows, deepCountryFilter, deepStoreFilter]);

  const deepLastScrapedScopedRows = useMemo(() => {
    const rows = deepLastScrapedRows || [];
    return rows
      .filter((row) => (deepCountryFilter ? row.country === deepCountryFilter : true))
      .filter((row) => (deepStoreFilter ? row.store === deepStoreFilter : true));
  }, [deepLastScrapedRows, deepCountryFilter, deepStoreFilter]);

  const deepPreviousWeeklyScopedRows = useMemo(() => {
    if (!deepPreviousWeekStart) return [];

    const rows = deepPreviousWeeklySummaryRows || [];
    return rows
      .filter((row) => (deepCountryFilter ? row.country === deepCountryFilter : true))
      .filter((row) => (deepStoreFilter ? row.store === deepStoreFilter : true));
  }, [deepPreviousWeekStart, deepPreviousWeeklySummaryRows, deepCountryFilter, deepStoreFilter]);

  const deepStoreCountryFromSummary = useMemo(() => {
    const map: Record<string, string | null> = {};
    deepWeeklyScopedRows.forEach((row) => {
      if (!row.store) return;
      map[row.store] = row.country ?? map[row.store] ?? null;
    });
    return map;
  }, [deepWeeklyScopedRows]);

  const deepWeeklyAvailableRows = useMemo(
    () =>
      deepWeeklyScopedRows.filter(
        (row) =>
          (row.dataStatus === "OK" || row.dataStatus === "PARTIAL") &&
          typeof row.priceEur === "number" &&
          Number.isFinite(row.priceEur),
      ),
    [deepWeeklyScopedRows],
  );

  const deepPreviousWeeklyAvailableRows = useMemo(
    () =>
      deepPreviousWeeklyScopedRows.filter(
        (row) =>
          (row.dataStatus === "OK" || row.dataStatus === "PARTIAL") &&
          typeof row.priceEur === "number" &&
          Number.isFinite(row.priceEur),
      ),
    [deepPreviousWeeklyScopedRows],
  );

  const deepComputedKpis = useMemo(() => {
    const stores = new Set<string>();
    const countries = new Set<string>();
    const prices: number[] = [];
    const unitPrices: number[] = [];
    let unitLabel: string | null = null;

    deepWeeklyAvailableRows.forEach((row) => {
      stores.add(row.store);
      if (row.country) countries.add(row.country);
      prices.push(row.priceEur as number);

      if (!unitLabel && typeof row.unitLabel === "string" && row.unitLabel.trim()) {
        unitLabel = row.unitLabel.trim();
      }
      if (typeof row.unitPriceEur === "number" && Number.isFinite(row.unitPriceEur)) {
        unitPrices.push(row.unitPriceEur);
      }
    });

    const avg = prices.length ? +(prices.reduce((s, v) => s + v, 0) / prices.length).toFixed(2) : null;
    const max = prices.length ? +Math.max(...prices).toFixed(2) : null;
    const min = prices.length ? +Math.min(...prices).toFixed(2) : null;

    const avgUnit = unitPrices.length
      ? +(unitPrices.reduce((s, v) => s + v, 0) / unitPrices.length).toFixed(2)
      : null;

    const discountPercents: number[] = [];
    deepLastScrapedScopedRows
      .filter((row) => row.dataStatus === "OK" || row.dataStatus === "PARTIAL")
      .forEach((row) => {
        if (typeof row.basePrice !== "number" || !Number.isFinite(row.basePrice)) return;
        if (typeof row.price !== "number" || !Number.isFinite(row.price)) return;
        if (row.basePrice <= 0) return;
        if (row.basePrice <= row.price) return;
        discountPercents.push(((row.basePrice - row.price) / row.basePrice) * 100);
      });

    const hasDiscountOffers = discountPercents.length > 0;
    const avgDiscountPct = hasDiscountOffers
      ? +(discountPercents.reduce((s, v) => s + v, 0) / discountPercents.length).toFixed(1)
      : 0;

    return {
      stores: stores.size,
      countries: countries.size,
      avgPriceEur: avg,
      maxPriceEur: max,
      minPriceEur: min,
      avgUnitPriceEur: avgUnit,
      unitLabel,
      avgDiscountPct,
      hasDiscountOffers,
    };
  }, [deepWeeklyAvailableRows, deepLastScrapedScopedRows]);

  const deepAvgWoW = useMemo(() => {
    const current = deepComputedKpis.avgPriceEur;
    if (typeof current !== "number" || !Number.isFinite(current)) return null;

    const previousValues = deepPreviousWeeklyAvailableRows
      .map((row) => row.priceEur)
      .filter((value): value is number => typeof value === "number" && Number.isFinite(value));

    if (!previousValues.length) return null;
    const previousRaw = previousValues.reduce((sum, value) => sum + value, 0) / previousValues.length;
    if (!Number.isFinite(previousRaw) || previousRaw <= 0) return null;

    // Keep the delta consistent with the displayed Avg (EUR), which is rounded to 2 decimals.
    // This avoids cases like 5.21 vs 5.21 showing -0.1% due to higher-precision intermediate values.
    const previous = +previousRaw.toFixed(2);
    if (!Number.isFinite(previous) || previous <= 0) return null;

    const pct = ((current - previous) / previous) * 100;
    if (!Number.isFinite(pct)) return null;
    const rounded = +pct.toFixed(1);

    return {
      pct: rounded,
      direction: rounded > 0 ? "up" : rounded < 0 ? "down" : "flat",
    } as const;
  }, [deepComputedKpis.avgPriceEur, deepPreviousWeeklyAvailableRows]);

  const deepCoverageInsight = useMemo(() => {
    const trackedStores = new Set<string>();

    const universe = deepStoreUniverse && deepStoreUniverse.length
      ? deepStoreUniverse
      : [];

    if (deepStoreFilter) {
      trackedStores.add(deepStoreFilter);
    } else if (universe.length) {
      universe.forEach((row) => trackedStores.add(row.store));
    } else {
      deepWeeklyScopedRows.forEach((row) => {
        if (row.store) trackedStores.add(row.store);
      });
    }

    const availableStores = new Set<string>();
    deepWeeklyAvailableRows.forEach((row) => availableStores.add(row.store));

    const missing = Array.from(trackedStores)
      .filter((store) => !availableStores.has(store))
      .sort((a, b) => a.localeCompare(b));

    const missingLabels = missing.map((store) =>
      formatStoreLabel(
        store,
        deepStoreUniverseMap[store] ?? deepStoreCountryFromSummary[store] ?? deepStoreCountryMap[store] ?? null,
      ),
    );

    const truncatedMissingLabels = missingLabels.length > 12 ? missingLabels.slice(0, 12) : missingLabels;
    const remainingMissing = missingLabels.length - truncatedMissingLabels.length;

    return {
      totalStores: trackedStores.size,
      availableStores: availableStores.size,
      missingLabels: truncatedMissingLabels,
      remainingMissing,
    };
  }, [
    deepWeeklyAvailableRows,
    deepWeeklyScopedRows,
    deepStoreCountryFromSummary,
    deepStoreCountryMap,
    deepStoreFilter,
    deepStoreUniverse,
    deepStoreUniverseMap,
  ]);

  const deepBarData = useMemo(() => {
    const discountByStore = new Map<string, number>();
    for (const row of deepLastScrapedScopedRows) {
      if (!row.store) continue;
      if (row.dataStatus !== "OK" && row.dataStatus !== "PARTIAL") continue;
      if (row.isDiscounted !== true) continue;
      if (typeof row.basePrice !== "number" || !Number.isFinite(row.basePrice)) continue;
      if (typeof row.price !== "number" || !Number.isFinite(row.price)) continue;
      if (row.basePrice <= 0) continue;
      if (row.basePrice <= row.price) continue;

      const pct = ((row.basePrice - row.price) / row.basePrice) * 100;
      if (!Number.isFinite(pct) || pct <= 0) continue;
      const rounded = +pct.toFixed(1);
      const prev = discountByStore.get(row.store);
      discountByStore.set(row.store, prev === undefined ? rounded : Math.max(prev, rounded));
    }

    const byStore = new Map<string, { store: string; price: number | null }>();
    for (const row of deepWeeklyAvailableRows) {
      if (!byStore.has(row.store)) {
        byStore.set(row.store, { store: row.store, price: row.priceEur });
      }
    }

    return Array.from(byStore.values())
      .map((item) => ({
        store: item.store,
        price: item.price,
        discountPct: discountByStore.get(item.store) ?? null,
      }))
      .sort((a, b) => {
        if (a.price === null) return 1;
        if (b.price === null) return -1;
        return a.price - b.price;
      });
  }, [deepWeeklyAvailableRows, deepLastScrapedScopedRows]);

  const deepBarDomain = useMemo(() => {
    const values = deepBarData.map((item) => item.price).filter((v): v is number => typeof v === "number");
    return computePaddedDomain(values);
  }, [deepBarData]);

  const [deepStoreSeries, setDeepStoreSeries] = useState<Record<string, TimeseriesRow[]> | null>(null);
  const [deepHiddenStores, setDeepHiddenStores] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    let mounted = true;

    async function loadPerStore() {
      setDeepStoreSeries(null);
      setDeepHiddenStores(new Set());

      if (!Number.isFinite(deepPid) || deepPid <= 0) return;
      if (!deepAnalysis) return;

      const stores = deepStoreFilter
        ? [deepStoreFilter]
        : (deepAnalysis.storeShare || []).map((s) => s.store).slice(0, 6);
      if (!stores.length) return;

      const promises = stores.map((store) =>
        getTimeseries(
          deepPid,
          undefined,
          deepCountryFilter,
          deepTrendWeeks,
          store,
          deepWeekStart || undefined,
        ).catch(() => []),
      );
      const results = await Promise.all(promises);
      if (!mounted) return;

      const map: Record<string, TimeseriesRow[]> = {};
      stores.forEach((s, i) => (map[s] = results[i]));
      setDeepStoreSeries(map);
    }

    loadPerStore();
    return () => {
      mounted = false;
    };
  }, [deepPid, deepAnalysis, deepCountryFilter, deepStoreFilter, deepTrendWeeks, deepWeekStart]);

  const deepTrendData = useMemo(() => {
    if (!deepStoreSeries) return [] as Record<string, any>[];

    const byWeek = new Map<string, Record<string, any>>();
    Object.entries(deepStoreSeries).forEach(([store, rows]) => {
      rows.forEach((r) => {
        const key = r.weekStart;
        const entry = byWeek.get(key) || { week: key };
        entry[store] = r.avgPriceEur;
        byWeek.set(key, entry);
      });
    });

    const axis = buildWeeklyAxis(Array.from(byWeek.keys()));
    return axis.map((week) => {
      const entry = byWeek.get(week) || { week };
      const values = Object.keys(entry)
        .filter((k) => k !== "week")
        .map((k) => entry[k])
        .filter((v) => typeof v === "number") as number[];
      const avg = values.length ? +(values.reduce((s, v) => s + v, 0) / values.length).toFixed(2) : null;
      return { ...entry, avg };
    });
  }, [deepStoreSeries]);

  const deepTrendDomain = useMemo(() => {
    const values: number[] = [];
    deepTrendData.forEach((row: any) => {
      Object.entries(row).forEach(([key, value]) => {
        if (key === "week") return;
        if (typeof value === "number" && Number.isFinite(value)) values.push(value);
      });
    });
    return computePaddedDomain(values);
  }, [deepTrendData]);

  const pieChartConfig = useMemo(() => ({ value: { label: "Products" } }), []);

  return (
    <div className="min-h-[calc(100vh-5.5rem)] overflow-auto p-3">
      <div className="flex flex-col gap-3">
        {/* Section A: Market Context */}
        <section className="order-2 rounded-xl border border-border/60 bg-background/70 p-3">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="h-8 w-1 rounded-full bg-[hsl(var(--cho-teal))]" />
              <div>
                <p className="text-sm font-semibold text-foreground">Market Context</p>
                <p className="text-[11px] text-muted-foreground">Unit price (EUR/L)</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Select value={marketCountry} onValueChange={setMarketCountry}>
                <SelectTrigger className="h-9 w-[180px] rounded-lg">
                  <SelectValue placeholder="Country" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All countries</SelectItem>
                  {(filters?.countries || []).map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={marketStore} onValueChange={setMarketStore}>
                <SelectTrigger className="h-9 w-[220px] rounded-lg">
                  <SelectValue placeholder="Store" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All stores</SelectItem>
                  {marketStoreOptions.map((value) => (
                    <SelectItem key={value} value={value}>
                      {formatStoreLabel(value, marketStoreCountryMap[value])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={marketWeekStart} onValueChange={setMarketWeekStart}>
                <SelectTrigger className="h-9 w-[190px] rounded-lg">
                  <SelectValue>
                    {marketWeekStart ? `Week •  ${formatWeekLabel(marketWeekStart)}` : "Select week"}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {marketWeeks.map((value) => (
                    <SelectItem key={value} value={value}>
                      {formatWeekLabel(value)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="mb-3 grid grid-cols-2 gap-2 lg:grid-cols-7">
            <KpiCard accent="teal" label="Products" value={marketOverview ? String(marketOverview.kpis.products) : "-"} />
            <KpiCard accent="teal" label="Stores" value={marketOverview ? String(marketOverview.kpis.stores) : "-"} />
            <KpiCard accent="teal" label="Countries" value={marketOverview ? String(marketOverview.kpis.countries) : "-"} />
            <KpiCard
              accent="gold"
              label={`Avg (${marketOverview?.kpis.unitLabel || "EUR/L"})`}
              value={
                marketOverview ? (
                  <>
                    <span className="text-lg font-bold text-[hsl(var(--cho-gold-dark))] tabular-nums leading-none tracking-tight">
                      {formatNumber(marketOverview.kpis.avgUnitPriceEur)}
                    </span>
                      {marketAvgWoW ? (
                        <span className="mt-1 flex items-center gap-1 text-[11px] font-medium tabular-nums">
                          <span
                            className={cn(
                              "text-sm leading-none",
                              marketAvgWoW.direction === "up"
                                ? "text-[hsl(var(--cho-teal))]"
                                : marketAvgWoW.direction === "down"
                                  ? "text-red-500"
                                  : "text-muted-foreground",
                            )}
                          >
                            {marketAvgWoW.direction === "up" ? "▲" : marketAvgWoW.direction === "down" ? "▼" : "—"}
                          </span>

                          <span className="text-foreground">
                            {marketAvgWoW.pct > 0 ? "+" : ""}
                            {marketAvgWoW.pct.toFixed(1)}%
                          </span>

                          <span className="ml-1 text-muted-foreground">vs last week</span>
                        </span>
                      ) : null}

                      {marketPreviousWeekStart ? (
                        <button
                          type="button"
                          onClick={() => setMarketChangesOpen((prev) => !prev)}
                          className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground"
                        >
                          {marketChangesOpen ? "Hide drivers" : "See drivers"}
                          <span className="text-[10px]">{marketChangesOpen ? "▲" : "▼"}</span>
                        </button>
                      ) : null}
                  </>
                ) : (
                  "-"
                )
              }
            />
            <KpiCard
              accent="gold"
              label={`Highest (${marketOverview?.kpis.unitLabel || "EUR/L"})`}
              value={marketOverview ? (
                <span className="text-[hsl(var(--cho-gold-dark))]">{formatNumber(marketOverview.kpis.maxUnitPriceEur)}</span>
              ) : "-"}
            />
            <KpiCard
              accent="gold"
              label={`Lowest (${marketOverview?.kpis.unitLabel || "EUR/L"})`}
              value={marketOverview ? (
                <span className="text-[hsl(var(--cho-teal))]">{formatNumber(marketOverview.kpis.minUnitPriceEur)}</span>
              ) : "-"}
            />
            <KpiCard
              accent="gold"
              label="Avg Discount"
              value={
                marketOverview
                  ? marketOverview.kpis.avgDiscountPct === null
                    ? (
                        <div className="flex flex-col">
                          <span className="text-lg font-semibold text-foreground tabular-nums leading-none tracking-tight">0%</span>
                          <span className="mt-1 block max-w-full overflow-hidden text-ellipsis whitespace-nowrap text-[10px] font-normal leading-tight text-muted-foreground">
                            — No promotions
                          </span>
                        </div>
                      )
                    : (
                        <span className="text-lg font-bold text-[hsl(var(--cho-gold-dark))] tabular-nums">
                          {formatPercent(marketOverview.kpis.avgDiscountPct)}
                        </span>
                      )
                  : "-"
              }
            />
          </div>

          {marketChangesOpen ? (
            <div className="mb-3 rounded-xl border border-border/60 bg-background/80 p-2">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2 border-b border-border/30 pb-2">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-[hsl(var(--cho-gold))]" />
                  <p className="text-xs font-semibold text-foreground">What moved Avg (EUR/L)?</p>
                  {marketWeekStart && marketPreviousWeekStart ? (
                    <p className="text-[11px] text-muted-foreground">
                      {formatWeekLabel(marketWeekStart)} vs {formatWeekLabel(marketPreviousWeekStart)}
                    </p>
                  ) : null}
                </div>

                <p className="text-[11px] text-muted-foreground">Top 15 by |% change|</p>
              </div>

              {marketChangesLoading ? (
                <p className="px-2 py-6 text-sm text-muted-foreground">Loading changes…</p>
              ) : !marketPreviousWeekStart ? (
                <p className="px-2 py-6 text-sm text-muted-foreground">No previous week available for comparison.</p>
              ) : marketChangesRows.length ? (
                <Table className="w-full">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[44%]">Product</TableHead>
                      <TableHead className="w-[28%]">This vs last week</TableHead>
                      <TableHead className="w-[18%]">Δ%</TableHead>
                      <TableHead className="w-[10%]">Screenshot</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {marketChangesRows.map((row) => {
                      const deltaPct = typeof row.deltaPct === "number" ? row.deltaPct : null;
                      const deltaDir = deltaPct === null ? "flat" : deltaPct > 0 ? "up" : deltaPct < 0 ? "down" : "flat";
                      const screenshotUrl = resolveStorageUrl(row.screenshotPath);

                      return (
                        <TableRow key={row.productVariantId}>
                          <TableCell>
                            <div className="flex flex-col">
                              {row.sourceUrl ? (
                                <a
                                  href={row.sourceUrl}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="font-medium text-foreground hover:underline"
                                >
                                  {row.product}
                                </a>
                              ) : (
                                <span className="font-medium text-foreground">{row.product}</span>
                              )}
                              <span className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                                {row.exampleStore ? <span>{row.exampleStore}</span> : null}
                                {row.exampleCountry ? <span>• {row.exampleCountry}</span> : null}
                                {row.hasDiscount ? (
                                  <span className="rounded-md border border-border/60 bg-muted/40 px-1.5 py-0.5 text-[10px] font-semibold text-foreground">
                                    Discount
                                  </span>
                                ) : null}
                              </span>
                            </div>
                          </TableCell>

                          <TableCell>
                            <div className="flex flex-col gap-0.5">
                              <span className="font-mono text-sm tabular-nums text-foreground">
                                {formatNumber(row.thisWeekUnitPriceEur)}
                              </span>
                              <span className="text-[11px] text-muted-foreground">
                                was {formatNumber(row.lastWeekUnitPriceEur)}
                              </span>
                            </div>
                          </TableCell>

                          <TableCell>
                            <div className="flex items-center gap-2">
                              <span
                                className={cn(
                                  "text-sm leading-none",
                                  deltaDir === "up"
                                    ? "text-[hsl(var(--cho-teal))]"
                                    : deltaDir === "down"
                                      ? "text-red-500"
                                      : "text-muted-foreground",
                                )}
                              >
                                {deltaDir === "up" ? "▲" : deltaDir === "down" ? "▼" : "—"}
                              </span>
                              <span className="font-mono text-sm tabular-nums text-foreground">
                                {deltaPct === null ? "-" : `${deltaPct > 0 ? "+" : ""}${deltaPct.toFixed(1)}%`}
                              </span>
                            </div>
                          </TableCell>

                          <TableCell>
                            {screenshotUrl ? (
                              <a href={screenshotUrl} target="_blank" rel="noreferrer" className="block">
                                <img
                                  src={screenshotUrl}
                                  alt={`Screenshot for ${row.product}`}
                                  className="h-10 w-16 rounded-md border border-border/60 object-cover"
                                  loading="lazy"
                                />
                              </a>
                            ) : (
                              <span className="text-sm text-muted-foreground">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              ) : (
                <p className="px-2 py-6 text-sm text-muted-foreground">No products changed vs the previous week for these filters.</p>
              )}
            </div>
          ) : null}

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div className="rounded-xl border border-border/60 bg-background/80 p-2">
              <div className="mb-2 flex items-center justify-between border-b border-border/30 pb-2">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-[hsl(var(--cho-teal))]" />
                  <p className="text-xs font-semibold text-foreground">Store ranking</p>
                </div>
                <p className="text-[11px] text-muted-foreground">Avg unit price</p>
              </div>

              <ChartContainer config={{ value: { label: "Unit price" } }} className="aspect-auto h-[280px] w-full">
                <BarChart data={marketRankingsData} layout="vertical" margin={{ top: 6, right: 10, left: 10, bottom: 6 }}>
                  <defs>
                    <linearGradient id="storeRankGradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="hsl(var(--cho-teal-light))" />
                      <stop offset="100%" stopColor="hsl(var(--cho-teal))" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid horizontal={false} stroke="hsl(var(--border)/0.5)" />
                  <XAxis type="number" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis
                    type="category"
                    dataKey="store"
                    width={120}
                    tick={{ fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value) =>
                      formatStoreLabel(String(value), marketStoreCountryMap[String(value)])
                    }
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value, _name, item) => {
                          const numeric = typeof value === "number" ? value : null;
                          const store = String(item?.payload?.store || "");
                          const label = formatStoreLabel(store, marketStoreCountryMap[store]);
                          return (
                            <div className="flex w-full items-center justify-between gap-6">
                              <span className="text-muted-foreground">{label}</span>
                              <span className="font-mono font-medium tabular-nums text-foreground">
                                {numeric === null
                                  ? "-"
                                  : `${formatNumber(numeric)} ${marketOverview?.kpis.unitLabel || "EUR/L"}`}
                              </span>
                            </div>
                          );
                        }}
                      />
                    }
                  />
                  <Bar dataKey="value" fill="url(#storeRankGradient)" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ChartContainer>
            </div>

            <div className="rounded-xl border border-border/60 bg-background/80 p-2">
              <div className="mb-2 flex items-center gap-2 border-b border-border/30 pb-2">
                <div className="h-2 w-2 rounded-full bg-[hsl(var(--cho-gold))]" />
                <p className="text-xs font-semibold text-foreground">Product Distribution Share by Retailer</p>
              </div>

              <ChartContainer config={pieChartConfig} className="aspect-auto h-[260px] w-full">
                <PieChart>
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value, _name, item) => {
                          const numeric = typeof value === "number" ? value : null;
                          const label = String(item?.payload?.name || "");
                          const count = numeric === null ? null : Math.round(numeric);
                          const pct =
                            numeric !== null && marketPresenceTotal > 0
                              ? (numeric / marketPresenceTotal) * 100
                              : null;

                          return (
                            <div className="flex w-full items-center justify-between gap-6">
                              <span className="text-muted-foreground">{label}</span>
                              <span className="font-mono font-medium tabular-nums text-foreground whitespace-nowrap">
                                {count === null
                                  ? "-"
                                  : `${count.toLocaleString()} ${count === 1 ? "product" : "products"}`}
                                <span className="text-muted-foreground">{" "}•{" "}</span>
                                {pct === null ? "-" : `${pct.toFixed(1)}%`}
                              </span>
                            </div>
                          );
                        }}
                      />
                    }
                  />
                  <Pie
                    data={marketPresenceChartData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={52}
                    outerRadius={86}
                    paddingAngle={2}
                  >
                    {marketPresenceChartData.map((slice, index) => (
                      <Cell
                        key={`cell-${slice.name}-${index}`}
                        fill={
                          slice.name === "Others"
                            ? OTHERS_COLOR
                            : PRESENCE_SLICE_COLORS[index] || PRESENCE_SLICE_COLORS[0]
                        }
                      />
                    ))}
                  </Pie>
                  <Legend />
                </PieChart>
              </ChartContainer>
            </div>
          </div>
        </section>

        {/* Section B: Product Performance */}
        <section className="order-1 rounded-xl border border-border/60 bg-background/70 p-3">
          <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="h-8 w-1 rounded-full bg-[hsl(var(--cho-gold))]" />
              <div>
                <p className="text-sm font-semibold text-foreground">Product Performance</p>
                <p className="text-[11px] text-muted-foreground">Selected product</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Select value={deepProductVariantId} onValueChange={setDeepProductVariantId}>
                <SelectTrigger className="h-9 w-[320px] rounded-lg">
                  <SelectValue placeholder="Product" />
                </SelectTrigger>
                <SelectContent>
                  {productOptions.map((product) => (
                    <SelectItem key={product.productVariantId} value={String(product.productVariantId)}>
                      {product.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={deepCountry} onValueChange={setDeepCountry}>
                <SelectTrigger className="h-9 w-[180px] rounded-lg">
                  <SelectValue placeholder="Country" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All countries</SelectItem>
                  {(filters?.countries || []).map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={deepStore} onValueChange={setDeepStore}>
                <SelectTrigger className="h-9 w-[220px] rounded-lg">
                  <SelectValue placeholder="Store" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All stores</SelectItem>
                  {deepStoreOptions.map((value) => (
                    <SelectItem key={value} value={value}>
                      {formatStoreLabel(value, deepStoreCountryMap[value])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

                <Select value={deepWeekStart} onValueChange={setDeepWeekStart}>
                  <SelectTrigger className="h-9 w-[190px] rounded-lg">
                    <SelectValue>
                      {deepWeekStart ? `Week •  ${formatWeekLabel(deepWeekStart)}` : "Select week"}
                    </SelectValue>
                  </SelectTrigger>
                <SelectContent>
                  {deepWeekOptions.map((value) => (
                    <SelectItem key={value} value={value}>
                      {formatWeekLabel(value)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="mb-3 grid grid-cols-2 gap-2 lg:grid-cols-6">
            <KpiCard accent="gold" label="Stores" value={deepWeeklySummaryRows ? String(deepComputedKpis.stores) : "-"} />
            <KpiCard accent="gold" label="Countries" value={deepWeeklySummaryRows ? String(deepComputedKpis.countries) : "-"} />
            <KpiCard
              accent="teal"
              label="Avg (EUR)"
              value={
                deepWeeklySummaryRows ? (
                  <>
                    <span className="text-lg font-bold text-[hsl(var(--cho-teal))] tabular-nums leading-none tracking-tight">
                      {formatNumber(deepComputedKpis.avgPriceEur)}
                    </span>
                      {deepAvgWoW ? (
                        <span className="mt-1 flex items-center gap-1 text-[11px] font-medium tabular-nums">
                          <span
                            className={cn(
                              "text-sm leading-none",
                              deepAvgWoW.direction === "up"
                                ? "text-[hsl(var(--cho-teal))]"
                                : deepAvgWoW.direction === "down"
                                  ? "text-red-500"
                                  : "text-muted-foreground",
                            )}
                          >
                            {deepAvgWoW.direction === "up"
                              ? "▲"
                              : deepAvgWoW.direction === "down"
                                ? "▼"
                                : "—"}
                          </span>

                          <span className="text-foreground">
                            {deepAvgWoW.pct > 0 ? "+" : ""}
                            {deepAvgWoW.pct.toFixed(1)}%
                          </span>

                          <span className="ml-1 text-muted-foreground">vs last week</span>
                        </span>
                      ) : null}
                  </>
                ) : (
                  "-"
                )
              }
            />
            <KpiCard
              accent="teal"
              label="Highest (EUR)"
              value={deepWeeklySummaryRows ? (
                <span className="text-[hsl(var(--cho-teal))]">{formatNumber(deepComputedKpis.maxPriceEur)}</span>
              ) : "-"}
            />
            <KpiCard
              accent="teal"
              label="Lowest (EUR)"
              value={deepWeeklySummaryRows ? (
                <span className="text-[hsl(var(--cho-gold-dark))]">{formatNumber(deepComputedKpis.minPriceEur)}</span>
              ) : "-"}
            />
            <KpiCard
              accent="gold"
              label="Discount"
              value={
                deepWeeklySummaryRows
                  ? deepComputedKpis.hasDiscountOffers
                    ? (
                        <span className="text-lg font-bold text-[hsl(var(--cho-gold-dark))] tabular-nums">
                          {formatPercent(deepComputedKpis.avgDiscountPct)}
                        </span>
                      )
                    : (
                        <>
                          <span className="text-lg font-semibold text-foreground tabular-nums leading-none tracking-tight">
                            0%
                          </span>
                          <span className="mt-1 block max-w-full overflow-hidden text-ellipsis whitespace-nowrap text-[10px] font-normal leading-tight text-muted-foreground">
                            — No promotions
                          </span>
                        </>
                      )
                  : "-"
              }
            />
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div className="rounded-xl border border-border/60 bg-background/80 p-2">
              <div className="mb-2 flex items-center justify-between gap-2 border-b border-border/30 pb-2">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-[hsl(var(--cho-teal))]" />
                  <div>
                    <p className="text-xs font-semibold text-foreground">Price per store</p>
                    <p className="text-[11px] text-muted-foreground">Weekly average price for selected week</p>
                  </div>
                </div>
              </div>

              <ChartContainer config={{ price: { label: "EUR" } }} className="aspect-auto h-[300px] w-full">
                <BarChart data={deepBarData} margin={{ top: 18, right: 8, left: 6, bottom: 26 }}>
                  <defs>
                    <linearGradient id="deepPriceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--cho-teal-light))" />
                      <stop offset="100%" stopColor="hsl(var(--cho-teal))" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="hsl(var(--border)/0.5)" />
                  <XAxis
                    dataKey="store"
                    tick={{ fontSize: 10 }}
                    interval={0}
                    angle={-25}
                    textAnchor="end"
                    height={44}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value) => formatStoreLabel(String(value), deepStoreCountryMap[String(value)])}
                  />
                  <YAxis
                    tick={{ fontSize: 10 }}
                    width={44}
                    domain={deepBarDomain ? [deepBarDomain.min, deepBarDomain.max] : ["dataMin", "dataMax"]}
                    tickFormatter={(value) => formatAxisNumber(Number(value))}
                    axisLine={false}
                    tickLine={false}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value, _name, item) => {
                          const numeric = typeof value === "number" ? value : null;
                          const store = String(item?.payload?.store || "");
                          const label = formatStoreLabel(store, deepStoreCountryMap[store]);
                          const discountPct = typeof item?.payload?.discountPct === "number" ? item.payload.discountPct : null;
                          return (
                            <div className="flex w-full items-center justify-between gap-6">
                              <div className="flex flex-col">
                                <span className="text-muted-foreground">{label}</span>
                                {discountPct !== null ? (
                                  <span className="mt-0.5 text-[11px] font-medium text-[hsl(var(--cho-gold-dark))]">
                                    Discount: -{discountPct.toFixed(1)}%
                                  </span>
                                ) : null}
                              </div>
                              <span className="font-mono font-medium tabular-nums text-foreground whitespace-nowrap">
                                {numeric === null ? "-" : `${formatNumber(numeric)} EUR`}
                              </span>
                            </div>
                          );
                        }}
                      />
                    }
                  />
                  <Bar
                    dataKey="price"
                    fill="url(#deepPriceGradient)"
                    radius={[6, 6, 0, 0]}
                  >
                    <LabelList
                      dataKey="discountPct"
                      position="top"
                      formatter={(value: any) => {
                        const v = typeof value === "number" ? value : null;
                        if (v === null || !Number.isFinite(v) || v <= 0) return "";
                        return `-${v.toFixed(1)}%`;
                      }}
                      className="fill-[hsl(var(--cho-gold-dark))] text-[10px] font-semibold"
                    />
                  </Bar>
                </BarChart>
              </ChartContainer>

              {!deepBarData.length ? (
                <p className="mt-1 text-[11px] text-muted-foreground">No data for this selection.</p>
              ) : null}

              {deepWeeklySummaryRows && deepCoverageInsight.totalStores > 0 ? (
                <div className="mt-2 rounded-lg border border-border/60 bg-background/70 p-2">
                  <p className="text-[11px] font-semibold text-foreground">Store Coverage Insight</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    This product is listed in{" "}
                    <span className="font-semibold text-foreground tabular-nums">
                      {deepCoverageInsight.availableStores}
                    </span>{" "}
                    out of{" "}
                    <span className="font-semibold text-foreground tabular-nums">
                      {deepCoverageInsight.totalStores}
                    </span>{" "}
                    tracked stores.
                  </p>
                  {deepCoverageInsight.missingLabels.length ? (
                    <p className="mt-1 text-[11px] text-muted-foreground">
                      Not listed in: {deepCoverageInsight.missingLabels.join(", ")}
                      {deepCoverageInsight.remainingMissing > 0
                        ? ` (+${deepCoverageInsight.remainingMissing} more)`
                        : ""}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>

            <div className="rounded-xl border border-border/60 bg-background/80 p-2">
              <div className="mb-2 flex items-center justify-between gap-2 border-b border-border/30 pb-2">
                <div className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full bg-[hsl(var(--cho-gold))]" />
                  <div>
                    <p className="text-xs font-semibold text-foreground">Price trend over time</p>
                    <p className="text-[11px] text-muted-foreground">Weekly average (EUR)</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <p className="text-[11px] text-muted-foreground">Period</p>
                  <Select
                    value={String(deepTrendWeeks)}
                    onValueChange={(v) => setDeepTrendWeeks(v === "0" ? 0 : Number(v))}
                  >
                    <SelectTrigger className="h-8 w-[140px] rounded-lg">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={String(26)}>6 months</SelectItem>
                      <SelectItem value={String(52)}>1 year</SelectItem>
                      <SelectItem value={String(0)}>All history</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <ChartContainer config={{ avg: { label: "Avg" } }} className="aspect-auto h-[300px] w-full">
                {deepStoreSeries ? (
                  <LineChart data={deepTrendData} margin={{ top: 8, right: 10, left: 6, bottom: 10 }}>
                    <CartesianGrid vertical={false} stroke="hsl(var(--border)/0.5)" />
                    <XAxis
                      dataKey="week"
                      tick={{ fontSize: 10 }}
                      tickFormatter={(value) => formatWeekLabel(String(value))}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 10 }}
                      width={44}
                      domain={deepTrendDomain ? [deepTrendDomain.min, deepTrendDomain.max] : ["dataMin", "dataMax"]}
                      tickFormatter={(value) => formatAxisNumber(Number(value))}
                      axisLine={false}
                      tickLine={false}
                    />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Legend
                      onClick={(e: any) => {
                        const key = String(e?.dataKey || "");
                        if (!key || key === "avg") return;
                        setDeepHiddenStores((prev) => {
                          const next = new Set(prev);
                          if (next.has(key)) next.delete(key);
                          else next.add(key);
                          return next;
                        });
                      }}
                      formatter={(_value: any, entry: any) => {
                        const key = String(entry?.dataKey || "");
                        if (key === "avg") return "Avg";
                        return formatStoreLabel(key, deepStoreCountryMap[key]);
                      }}
                    />
                    {Object.keys(deepStoreSeries).map((store, idx) => (
                      <Line
                        key={store}
                        type="monotone"
                        dataKey={store}
                        name={formatStoreLabel(store, deepStoreCountryMap[store])}
                        stroke={PIE_COLORS[idx % PIE_COLORS.length]}
                        strokeWidth={2}
                        dot={false}
                        connectNulls={false}
                        hide={deepHiddenStores.has(store)}
                      />
                    ))}
                    <Line
                      type="monotone"
                      dataKey="avg"
                      name="Avg"
                      stroke="hsl(var(--cho-gold))"
                      strokeDasharray="4 4"
                      dot={false}
                      connectNulls={false}
                    />
                  </LineChart>
                ) : (
                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">No data.</div>
                )}
              </ChartContainer>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}