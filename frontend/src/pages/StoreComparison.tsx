import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import { getFilters, getSummary } from "@/lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";
import { Store, Trophy, AlertCircle, TrendingDown, Percent } from "lucide-react";

export default function StoreComparison() {
  const { data: filters } = useQuery({ queryKey: ["filters"], queryFn: getFilters });
  const { data: summary = [] } = useQuery({ queryKey: ["summary"], queryFn: () => getSummary() });

  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedCountry, setSelectedCountry] = useState("all");

  const activeProduct = selectedProduct || filters?.products?.[0] || "";

  const allData = useMemo(() => {
    return summary
      .filter((row) => row.product === activeProduct)
      .map((row) => ({
        store: row.store,
        country: row.country || "Unknown",
        storeLabel: `${row.store} · ${row.country || "Unknown"}`,
        priceOriginal: row.price,
        currency: row.currency,
        priceEur: row.priceEur ?? row.price,
        scrapedAt: row.weekStart,
      }))
      .sort((a, b) => a.priceEur - b.priceEur);
  }, [summary, activeProduct]);

  const countriesList = useMemo(() => [...new Set(allData.map((d) => d.country))].sort(), [allData]);
  const data = selectedCountry === "all" ? allData : allData.filter((d) => d.country === selectedCountry);

  const cheapest = data[0];
  const expensive = data[data.length - 1];
  const saving = cheapest && expensive ? expensive.priceEur - cheapest.priceEur : 0;
  const savingPct = cheapest && expensive && expensive.priceEur > 0 ? (saving / expensive.priceEur * 100) : 0;

  const chartConfig = { priceEur: { label: "Price (EUR)", color: "hsl(var(--cho-teal))" } };

  return (
    <div>
      <PageHeader icon={Store} title="Store Comparison" subtitle="Compare latest retail prices side by side across stores." />

      <div className="glass-card rounded-2xl p-5 mb-6 flex flex-wrap items-center gap-4">
        <div>
          <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Product</label>
          <Select value={activeProduct} onValueChange={setSelectedProduct}>
            <SelectTrigger className="w-64 h-10 rounded-xl bg-background/60 border-border/50"><SelectValue /></SelectTrigger>
            <SelectContent>{(filters?.products || []).map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div>
          <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Country</label>
          <Select value={selectedCountry} onValueChange={setSelectedCountry}>
            <SelectTrigger className="w-48 h-10 rounded-xl bg-background/60 border-border/50"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Countries</SelectItem>
              {countriesList.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <MetricCard
          label="Cheapest"
          value={cheapest ? `${cheapest.store} (${cheapest.country})` : "-"}
          icon={Trophy}
          accentColor="teal"
        />
        <MetricCard
          label="Most Expensive"
          value={expensive ? `${expensive.store} (${expensive.country})` : "-"}
          icon={AlertCircle}
          accentColor="gold"
        />
        <MetricCard label="Max Saving" value={`€${saving.toFixed(2)}`} icon={TrendingDown} />
        <MetricCard label="Saving %" value={`${savingPct.toFixed(1)}%`} icon={Percent} accentColor="teal" />
      </div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
        <div className="glass-card rounded-2xl p-6 mb-6">
          <ChartContainer config={chartConfig} className="h-[380px] w-full">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.5} />
              <XAxis dataKey="storeLabel" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} angle={-20} textAnchor="end" height={80} />
              <YAxis tickFormatter={(v) => `€${v.toFixed(1)}`} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="priceEur" fill="hsl(var(--cho-teal))" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ChartContainer>
        </div>
      </motion.div>

      {/* Ranking */}
      <div className="glass-card rounded-2xl p-6">
        <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
          <Trophy className="w-5 h-5 text-primary" /> Price Ranking
        </h3>
        <div className="space-y-2">
          {data.map((row, idx) => {
            const diff = row.priceEur - (cheapest?.priceEur || 0);
            const isFirst = idx === 0;
            const isLast = idx === data.length - 1;
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.03 }}
                className={`p-4 rounded-xl text-sm font-medium flex items-center justify-between transition-colors ${
                  isFirst ? "bg-accent/10 border border-accent/20 text-accent" :
                  isLast ? "bg-destructive/10 border border-destructive/20 text-destructive" :
                  "bg-muted/30 border border-border/50 text-foreground"
                }`}
              >
                <span>
                  <span className="font-bold">{isFirst ? "🏆" : `#${idx + 1}`}</span>
                  {" "}{row.store}
                  <span className="text-muted-foreground"> · {row.country}</span>
                </span>
                <span className="font-bold tabular-nums">
                  €{row.priceEur.toFixed(2)}
                  {diff > 0 && <span className="text-muted-foreground font-normal ml-2">(+€{diff.toFixed(2)})</span>}
                </span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
