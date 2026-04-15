import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import { getFilters, getSummary, resolveStorageUrl } from "@/lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Tag, Store, Calendar, TrendingDown, TrendingUp, Camera, ChevronLeft, ChevronRight, ExternalLink, Link2 } from "lucide-react";

export default function PricesExplorer() {
  const { data: filters } = useQuery({ queryKey: ["filters"], queryFn: getFilters });

  const [selectedProduct, setSelectedProduct] = useState("all");
  const [selectedCountry, setSelectedCountry] = useState("all");
  const [selectedWebsite, setSelectedWebsite] = useState("all");
  const [selectedStore, setSelectedStore] = useState("all");
  const [timeView, setTimeView] = useState("latest");
  const [page, setPage] = useState(1);

  const pageSize = 100;

  const includeAllWeeks = timeView === "all";

  const { data: allData = [] } = useQuery({
    queryKey: ["summary", includeAllWeeks ? "all-weeks" : "latest-week"],
    queryFn: () => getSummary(undefined, includeAllWeeks),
  });

  const products = useMemo(() => filters?.products || [], [filters]);
  const productScope = selectedProduct === "all" ? allData : allData.filter((d) => d.product === selectedProduct);
  const countries = useMemo(
    () => [...new Set(productScope.map((d) => d.country).filter(Boolean) as string[])].sort(),
    [productScope]
  );
  const countryScope = selectedCountry === "all" ? productScope : productScope.filter((d) => d.country === selectedCountry);
  const websitesList = useMemo(() => [...new Set(countryScope.map((d) => d.website))].sort(), [countryScope]);
  const websiteScope = selectedWebsite === "all" ? countryScope : countryScope.filter((d) => d.website === selectedWebsite);
  const storesList = useMemo(() => [...new Set(websiteScope.map((d) => d.store))].sort(), [websiteScope]);
  const storeScope = selectedStore === "all" ? websiteScope : websiteScope.filter((d) => d.store === selectedStore);
  const weeks = useMemo(() => [...new Set(storeScope.map((d) => d.weekStart))].sort().reverse(), [storeScope]);

  const filtered = useMemo(() => {
    if (timeView === "latest" && weeks.length > 0) return storeScope.filter((d) => d.weekStart === weeks[0]);
    return storeScope;
  }, [timeView, weeks, storeScope]);

  const sortedFiltered = useMemo(
    () =>
      [...filtered].sort(
        (a, b) =>
          b.weekStart.localeCompare(a.weekStart) ||
          (a.priceEur ?? Number.POSITIVE_INFINITY) - (b.priceEur ?? Number.POSITIVE_INFINITY),
      ),
    [filtered]
  );

  const totalPages = Math.max(1, Math.ceil(sortedFiltered.length / pageSize));

  useEffect(() => {
    setPage(1);
  }, [selectedProduct, selectedCountry, selectedWebsite, selectedStore, timeView]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const displayedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedFiltered.slice(start, start + pageSize);
  }, [sortedFiltered, page]);

  const pageStart = sortedFiltered.length === 0 ? 0 : (page - 1) * pageSize + 1;
  const pageEnd = Math.min(page * pageSize, sortedFiltered.length);

  const eurValues = useMemo(
    () => sortedFiltered.map((d) => d.priceEur).filter((v): v is number => typeof v === "number"),
    [sortedFiltered],
  );

  return (
    <div>
      <PageHeader icon={Tag} title="Prices Explorer" subtitle="Browse and filter weekly retail prices across all tracked stores." />

      {/* Filters */}
      <div className="glass-card rounded-2xl p-5 mb-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <FilterSelect label="Product" value={selectedProduct} onChange={setSelectedProduct} options={products} allLabel="All Products" />
          <FilterSelect label="Country" value={selectedCountry} onChange={setSelectedCountry} options={countries} allLabel="All Countries" />
          <FilterSelect label="Website" value={selectedWebsite} onChange={setSelectedWebsite} options={websitesList} allLabel="All Websites" />
          <FilterSelect label="Store" value={selectedStore} onChange={setSelectedStore} options={storesList} allLabel="All Stores" />
          <FilterSelect label="Time View" value={timeView} onChange={setTimeView} options={[]} allLabel="" customOptions={[
            { value: "latest", label: "Latest Week" },
            { value: "all", label: "All Weeks" },
          ]} />
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <MetricCard label="Products" value={new Set(sortedFiltered.map((d) => d.product)).size} icon={Tag} accentColor="gold" />
        <MetricCard label="Stores" value={new Set(sortedFiltered.map((d) => d.store)).size} icon={Store} />
        <MetricCard label="Weeks" value={new Set(sortedFiltered.map((d) => d.weekStart)).size} icon={Calendar} />
        <MetricCard label="Lowest" value={eurValues.length ? `€${Math.min(...eurValues).toFixed(2)}` : "-"} icon={TrendingDown} accentColor="teal" />
        <MetricCard label="Highest" value={eurValues.length ? `€${Math.max(...eurValues).toFixed(2)}` : "-"} icon={TrendingUp} accentColor="gold" />
      </div>

      {/* Table */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="overflow-auto max-h-[500px]">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Product</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Country</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Store</TableHead>
                  <TableHead className="text-right font-bold text-xs uppercase tracking-wider">Local Price</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Curr.</TableHead>
                  <TableHead className="text-right font-bold text-xs uppercase tracking-wider">EUR</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Link</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Screenshot</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Week</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayedRows.map((row, i) => (
                  <TableRow key={i} className="hover:bg-muted/20 transition-colors">
                    <TableCell className="font-semibold text-sm">{row.product}</TableCell>
                    <TableCell className="text-sm">{row.country}</TableCell>
                    <TableCell className="text-sm">{row.store}</TableCell>
                    <TableCell className="text-right text-sm tabular-nums">{row.price.toFixed(2)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground font-medium">{row.currency}</TableCell>
                    <TableCell className="text-right font-bold text-sm tabular-nums text-primary">
                      {row.priceEur === null ? "-" : `€${row.priceEur.toFixed(2)}`}
                    </TableCell>
                    <TableCell className="text-center">
                      {row.sourceUrl ? (
                        <Button variant="ghost" size="sm" className="h-8 px-2 rounded-lg" asChild>
                          <a href={row.sourceUrl} target="_blank" rel="noopener noreferrer">
                            <Link2 className="w-3.5 h-3.5 mr-1" /> Open <ExternalLink className="w-3 h-3 ml-1" />
                          </a>
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      {resolveStorageUrl(row.screenshotPath) ? (
                        <Button variant="ghost" size="sm" className="h-8 px-2 rounded-lg" asChild>
                          <a href={resolveStorageUrl(row.screenshotPath) || undefined} target="_blank" rel="noopener noreferrer">
                            <Camera className="w-3.5 h-3.5 mr-1" /> View <ExternalLink className="w-3 h-3 ml-1" />
                          </a>
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{row.weekStart}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        <div className="mt-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <p className="text-xs text-muted-foreground font-medium">
            {sortedFiltered.length === 0
              ? "0 price points"
              : `Showing ${pageStart}-${pageEnd} of ${sortedFiltered.length} price points`}
          </p>

          {sortedFiltered.length > pageSize && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 rounded-lg"
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                disabled={page <= 1}
              >
                <ChevronLeft className="w-4 h-4 mr-1" /> Prev
              </Button>
              <span className="text-xs text-muted-foreground font-medium min-w-[90px] text-center">
                Page {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="h-8 rounded-lg"
                onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={page >= totalPages}
              >
                Next <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

function FilterSelect({ label, value, onChange, options, allLabel, customOptions }: {
  label: string; value: string; onChange: (v: string) => void;
  options: string[]; allLabel: string;
  customOptions?: { value: string; label: string }[];
}) {
  return (
    <div>
      <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">{label}</label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="h-10 text-sm rounded-xl bg-background/60 border-border/50">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {customOptions ? (
            customOptions.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)
          ) : (
            <>
              <SelectItem value="all">{allLabel}</SelectItem>
              {options.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
            </>
          )}
        </SelectContent>
      </Select>
    </div>
  );
}
