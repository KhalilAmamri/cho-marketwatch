import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import { getFilters, getSummary, getTimeseries } from "@/lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Legend } from "recharts";
import { TrendingUp, TrendingDown, BarChart3, Activity } from "lucide-react";

export default function PriceTrends() {
  const { data: filters } = useQuery({ queryKey: ["filters"], queryFn: getFilters });
  const { data: summaryRows = [] } = useQuery({
    queryKey: ["summary", "all-weeks", "trends"],
    queryFn: () => getSummary(undefined, true),
  });

  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedCountry, setSelectedCountry] = useState("all");
  const [selectedWebsite, setSelectedWebsite] = useState("all");
  const [selectedStore, setSelectedStore] = useState("all");

  const activeProduct = selectedProduct || filters?.products?.[0] || "";

  const productScope = useMemo(
    () => summaryRows.filter((row) => row.product === activeProduct),
    [summaryRows, activeProduct],
  );
  const countries = useMemo(
    () => [...new Set(productScope.map((row) => row.country).filter(Boolean) as string[])].sort(),
    [productScope],
  );
  const countryScope = useMemo(
    () => (selectedCountry === "all" ? productScope : productScope.filter((row) => row.country === selectedCountry)),
    [productScope, selectedCountry],
  );
  const websites = useMemo(() => [...new Set(countryScope.map((row) => row.website))].sort(), [countryScope]);
  const websiteScope = useMemo(
    () => (selectedWebsite === "all" ? countryScope : countryScope.filter((row) => row.website === selectedWebsite)),
    [countryScope, selectedWebsite],
  );
  const stores = useMemo(() => [...new Set(websiteScope.map((row) => row.store))].sort(), [websiteScope]);

  useEffect(() => {
    if (selectedCountry !== "all" && !countries.includes(selectedCountry)) setSelectedCountry("all");
  }, [countries, selectedCountry]);

  useEffect(() => {
    if (selectedWebsite !== "all" && !websites.includes(selectedWebsite)) setSelectedWebsite("all");
  }, [websites, selectedWebsite]);

  useEffect(() => {
    if (selectedStore !== "all" && !stores.includes(selectedStore)) setSelectedStore("all");
  }, [stores, selectedStore]);

  const websiteFilter = selectedWebsite === "all" ? undefined : selectedWebsite;
  const countryFilter = selectedCountry === "all" ? undefined : selectedCountry;
  const storeFilter = selectedStore === "all" ? undefined : selectedStore;

  const { data: history = [], isLoading } = useQuery({
    queryKey: ["timeseries", activeProduct, websiteFilter || "all", countryFilter || "all", storeFilter || "all"],
    queryFn: () => getTimeseries(activeProduct, websiteFilter, countryFilter, 52, storeFilter),
    enabled: Boolean(activeProduct),
  });

  const chartData = useMemo(() => {
    return history.map((h) => ({ week: h.weekStart, price: h.avgPriceEur, samples: h.sampleCount }));
  }, [history]);

  const prices = useMemo(
    () => chartData.map((h) => h.price).filter((v): v is number => typeof v === "number"),
    [chartData],
  );
  const min = prices.length ? Math.min(...prices) : null;
  const max = prices.length ? Math.max(...prices) : null;
  const avg = prices.length ? prices.reduce((a, b) => a + b, 0) / prices.length : null;
  const spread = min !== null && max !== null ? max - min : null;

  const chartConfig = {
    price: { label: "Weekly avg EUR", color: "hsl(var(--cho-gold))" },
  };

  return (
    <div>
      <PageHeader
        icon={TrendingUp}
        title="Price Trends"
        subtitle="Track weekly average EUR prices with explicit scope filters (country, website, and store)."
      />

      <div className="glass-card rounded-2xl p-5 mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Product</label>
            <Select
              value={activeProduct}
              onValueChange={(value) => {
                setSelectedProduct(value);
                setSelectedCountry("all");
                setSelectedWebsite("all");
                setSelectedStore("all");
              }}
            >
              <SelectTrigger className="h-10 rounded-xl bg-background/60 border-border/50">
                <SelectValue placeholder="Select product" />
              </SelectTrigger>
              <SelectContent>
                {(filters?.products || []).map((p) => (
                  <SelectItem key={p} value={p}>{p}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <ScopeSelect
            label="Country"
            value={selectedCountry}
            onChange={(value) => {
              setSelectedCountry(value);
              setSelectedWebsite("all");
              setSelectedStore("all");
            }}
            options={countries}
            allLabel="All Countries"
          />

          <ScopeSelect
            label="Website"
            value={selectedWebsite}
            onChange={(value) => {
              setSelectedWebsite(value);
              setSelectedStore("all");
            }}
            options={websites}
            allLabel="All Websites"
          />

          <ScopeSelect
            label="Store"
            value={selectedStore}
            onChange={setSelectedStore}
            options={stores}
            allLabel="All Stores"
          />
        </div>

        <p className="text-xs text-muted-foreground font-medium">
          Logic: values are weekly averages in EUR for the selected product, aggregated over the current scope.
          Choose a specific store to get a store-only trend.
        </p>
      </div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
        {isLoading ? (
          <div className="glass-card rounded-2xl p-12 mb-6 text-center text-muted-foreground">Loading trend data...</div>
        ) : chartData.length === 0 ? (
          <div className="glass-card rounded-2xl p-12 mb-6 text-center text-muted-foreground">
            No trend data found for the selected scope.
          </div>
        ) : (
          <div className="glass-card rounded-2xl p-6 mb-6">
            <ChartContainer config={chartConfig} className="h-[400px] w-full">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.5} />
                <XAxis dataKey="week" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis tickFormatter={(v) => `€${Number(v).toFixed(1)}`} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="price"
                  name="Weekly avg EUR"
                  stroke="hsl(var(--cho-gold))"
                  strokeWidth={2.5}
                  dot={{ r: 2 }}
                  activeDot={{ r: 5 }}
                  connectNulls={false}
                />
              </LineChart>
            </ChartContainer>
          </div>
        )}
      </motion.div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Lowest" value={min === null ? "-" : `€${min.toFixed(2)}`} icon={TrendingDown} accentColor="teal" />
        <MetricCard label="Highest" value={max === null ? "-" : `€${max.toFixed(2)}`} icon={TrendingUp} accentColor="gold" />
        <MetricCard label="Average" value={avg === null ? "-" : `€${avg.toFixed(2)}`} icon={BarChart3} />
        <MetricCard label="Spread" value={spread === null ? "-" : `€${spread.toFixed(2)}`} icon={Activity} />
      </div>
    </div>
  );
}

function ScopeSelect({
  label,
  value,
  onChange,
  options,
  allLabel,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  allLabel: string;
}) {
  return (
    <div>
      <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">{label}</label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="h-10 rounded-xl bg-background/60 border-border/50">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">{allLabel}</SelectItem>
          {options.map((item) => (
            <SelectItem key={item} value={item}>{item}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
