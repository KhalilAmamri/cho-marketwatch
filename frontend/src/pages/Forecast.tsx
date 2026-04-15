import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { getFilters, getForecasts, getTimeseries } from "@/lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { Line, XAxis, YAxis, CartesianGrid, Area, ComposedChart } from "recharts";
import { Sparkles, Target, Database, Activity } from "lucide-react";
import { MetricCard } from "@/components/MetricCard";

export default function Forecast() {
  const { data: filters } = useQuery({ queryKey: ["filters"], queryFn: getFilters });
  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedStore, setSelectedStore] = useState("");

  const activeProduct = selectedProduct || filters?.products?.[0] || "";

  const { data: forecasts = [] } = useQuery({
    queryKey: ["forecasts", activeProduct],
    queryFn: () => getForecasts(activeProduct),
    enabled: Boolean(activeProduct),
  });

  const { data: history = [] } = useQuery({
    queryKey: ["timeseries", activeProduct, "forecast"],
    queryFn: () => getTimeseries(activeProduct, undefined, undefined, 26),
    enabled: Boolean(activeProduct),
  });

  const forecastStores = useMemo(() => [...new Set(forecasts.map((f) => f.store))].sort(), [forecasts]);

  const storeForecasts = selectedStore ? forecasts.filter((f) => f.store === selectedStore) : [];

  const chartData = useMemo(() => {
    const histPoints = history.map((h) => ({
      date: h.weekStart,
      historical: h.avgPriceEur,
      predicted: null as number | null,
      low: null as number | null,
      high: null as number | null,
    }));
    const forecastPoints = storeForecasts.map((f) => ({
      date: f.date,
      historical: null as number | null,
      predicted: f.pricePred,
      low: f.priceLow,
      high: f.priceHigh,
    }));
    return [...histPoints, ...forecastPoints].sort((a, b) => a.date.localeCompare(b.date));
  }, [history, storeForecasts]);

  const latestStoreForecast = storeForecasts.length ? storeForecasts[storeForecasts.length - 1] : null;
  const confidence = latestStoreForecast?.confidenceLevel || "Unknown";
  const trainingPoints = latestStoreForecast?.trainingPoints ?? 0;
  const coverageRate = latestStoreForecast?.coverageRate ?? null;
  const lastObservedWeek = latestStoreForecast?.lastObservedWeek ?? null;
  const coverageText = coverageRate === null ? "unknown" : `${coverageRate.toFixed(1)}%`;

  const chartConfig = {
    historical: { label: "Historical", color: "hsl(var(--cho-teal))" },
    predicted: { label: "Predicted", color: "hsl(var(--cho-gold))" },
  };

  return (
    <div>
      <PageHeader icon={Sparkles} title="Price Forecast" subtitle="Next 3 weeks forecast for the selected product and store." />

      <div className="glass-card rounded-2xl p-5 mb-6 flex flex-wrap items-center gap-4">
        <div>
          <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Product</label>
          <Select value={activeProduct} onValueChange={(v) => { setSelectedProduct(v); setSelectedStore(""); }}>
            <SelectTrigger className="w-72 h-10 rounded-xl bg-background/60 border-border/50"><SelectValue /></SelectTrigger>
            <SelectContent>{(filters?.products || []).map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Store</label>
          <Select value={selectedStore} onValueChange={setSelectedStore}>
            <SelectTrigger className="w-72 h-10 rounded-xl bg-background/60 border-border/50"><SelectValue placeholder="Select store" /></SelectTrigger>
            <SelectContent>{forecastStores.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
          </Select>
        </div>
      </div>

      {!selectedStore && (
        <div className="glass-card rounded-2xl p-16 text-center">
          <Sparkles className="w-12 h-12 text-primary/30 mx-auto mb-4" />
          <p className="text-muted-foreground font-medium">Select a store to view its price forecast</p>
        </div>
      )}

      {selectedStore && storeForecasts.length === 0 && (
        <div className="glass-card rounded-2xl p-16 text-center">
          <p className="text-muted-foreground font-medium">No saved forecasts for this store.</p>
        </div>
      )}

      {selectedStore && storeForecasts.length > 0 && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <MetricCard label="Confidence" value={confidence} icon={Target} accentColor="teal" />
            <MetricCard
              label="Training Weeks"
              value={trainingPoints}
              icon={Database}
            />
            <MetricCard
              label="Data Coverage"
              value={coverageRate === null ? "-" : `${coverageRate.toFixed(1)}%`}
              icon={Activity}
              trend="neutral"
              trendValue={lastObservedWeek ? `Last observed ${lastObservedWeek}` : "No history metadata"}
            />
          </div>

          <div className="glass-card rounded-2xl p-5 mb-6">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">How This Forecast Works</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <p className="text-sm font-semibold mb-2">Features Used</p>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li>Recent prices from the last 3 observed weeks.</li>
                  <li>Calendar timing: week of year and month.</li>
                  <li>How many prices we collected recently, and how long since the last observed price.</li>
                  <li>Product and store context: brand, category, format, packaging, website, country, and store code.</li>
                </ul>
              </div>
              <div>
                <p className="text-sm font-semibold mb-2">How To Read The Result</p>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li><span className="font-semibold text-foreground">Predicted</span>: expected average price for that week.</li>
                  <li><span className="font-semibold text-foreground">Low / High</span>: likely range, not a guaranteed limit.</li>
                  <li><span className="font-semibold text-foreground">Confidence</span>: higher when we have more history weeks and more consistent price patterns.</li>
                  <li>This selection uses <span className="font-semibold text-foreground">{trainingPoints}</span> training weeks with <span className="font-semibold text-foreground">{coverageText}</span> data coverage.</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="glass-card rounded-2xl p-6 mb-6">
            <h3 className="font-bold text-sm mb-4 text-muted-foreground uppercase tracking-wider">Historical vs Predicted — {selectedStore}</h3>
            <ChartContainer config={chartConfig} className="h-[380px] w-full">
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.5} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis tickFormatter={(v) => `€${Number(v).toFixed(1)}`} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Area dataKey="high" stackId="range" fill="hsl(var(--cho-gold) / 0.1)" stroke="none" />
                <Area dataKey="low" stackId="range" fill="transparent" stroke="none" />
                <Line type="monotone" dataKey="historical" stroke="hsl(var(--cho-teal))" strokeWidth={2.5} dot={{ r: 2 }} connectNulls={false} />
                <Line type="monotone" dataKey="predicted" stroke="hsl(var(--cho-gold))" strokeWidth={2.5} strokeDasharray="6 3" dot={{ r: 4 }} connectNulls={false} />
              </ComposedChart>
            </ChartContainer>
          </div>

          <div className="glass-card rounded-2xl overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Week</TableHead>
                  <TableHead className="text-right font-bold text-xs uppercase tracking-wider">Predicted</TableHead>
                  <TableHead className="text-right font-bold text-xs uppercase tracking-wider">Low</TableHead>
                  <TableHead className="text-right font-bold text-xs uppercase tracking-wider">High</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {storeForecasts.map((f, i) => (
                  <TableRow key={i} className="hover:bg-muted/20">
                    <TableCell className="font-medium">{f.date}</TableCell>
                    <TableCell className="text-right font-bold text-primary tabular-nums">€{f.pricePred.toFixed(2)}</TableCell>
                    <TableCell className="text-right text-muted-foreground tabular-nums">
                      {f.priceLow === null ? "-" : `€${f.priceLow.toFixed(2)}`}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground tabular-nums">
                      {f.priceHigh === null ? "-" : `€${f.priceHigh.toFixed(2)}`}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}
