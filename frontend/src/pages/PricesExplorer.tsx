import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { getFilters, getSummary, resolveStorageUrl, type PriceMode } from "@/lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import * as XLSX from "xlsx";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Tag,
  Camera,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Link2,
  RotateCcw,
  SlidersHorizontal,
  FileDown,
  X,
} from "lucide-react";

type TimeViewMode = "latest" | "specific" | "all";
type StatusFilter = "all" | "OK" | "PARTIAL" | "MISSING";

const NO_WEEK_OPTION = "__no_week__";

function uniqueSorted(values: string[]): string[] {
  return [...new Set(values.filter((value) => Boolean(value && value.trim())))].sort((a, b) => a.localeCompare(b));
}

export default function PricesExplorer() {
  const { data: filters } = useQuery({ queryKey: ["filters"], queryFn: getFilters });

  const [selectedBrand, setSelectedBrand] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedRangeName, setSelectedRangeName] = useState("all");
  const [selectedFormat, setSelectedFormat] = useState("all");
  const [selectedPackaging, setSelectedPackaging] = useState("all");
  const [selectedProductVariantId, setSelectedProductVariantId] = useState("all");
  const [selectedCountry, setSelectedCountry] = useState("all");
  const [selectedWebsite, setSelectedWebsite] = useState("all");
  const [selectedStore, setSelectedStore] = useState("all");
  const [selectedCurrency, setSelectedCurrency] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState<StatusFilter>("all");
  const [priceMode, setPriceMode] = useState<PriceMode>("average");
  const [timeView, setTimeView] = useState<TimeViewMode>("latest");
  const [selectedWeek, setSelectedWeek] = useState("");
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  const pageSize = 100;

  const exportToExcel = () => {
    const rows = sortedFiltered;
    if (!rows.length) return;

    const data = rows.map((row) => ({
      Brand: row.brand,
      Category: row.category,
      Range: row.rangeName,
      Format: row.format,
      Packaging: row.packaging,
      Country: row.country,
      Store: row.store,
      "Local Price": row.price === null ? "-" : row.price.toFixed(2),
      "Base Price": row.basePrice === null ? "-" : row.basePrice.toFixed(2),
      Currency: row.currency,
      "EUR Price": row.priceEur === null ? "-" : row.priceEur.toFixed(2),
      "Unit Price": row.unitPriceEur === null ? "-" : `${row.unitLabel || "EUR/L"} ${row.unitPriceEur.toFixed(2)}`,
      "Discount %":
        row.basePrice && row.price && row.basePrice > row.price
          ? (((row.basePrice - row.price) / row.basePrice) * 100).toFixed(0) + "%"
          : "0%",
      "Listing Status": statusLabel(row.dataStatus),
      "Link URL": row.sourceUrl || "-",
      "Screenshot URL": resolveStorageUrl(row.screenshotPath) || "-",
      Week: row.weekStart,
    }));

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Price Records");
    XLSX.writeFile(wb, `price-records-${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  const { data: allWeeksData = [] } = useQuery({
    queryKey: ["summary", "all-weeks", "explorer-options", priceMode],
    queryFn: () => getSummary(undefined, true, priceMode),
  });

  const specificWeek = timeView === "specific" ? selectedWeek : undefined;
  const includeAllWeeks = timeView === "all";

  const { data: summaryRows = [] } = useQuery({
    queryKey: ["summary", "explorer", priceMode, timeView, specificWeek || "none"],
    queryFn: () => getSummary(specificWeek || undefined, includeAllWeeks, priceMode),
    enabled: timeView !== "specific" || Boolean(specificWeek),
  });

  const resetFilters = () => {
    setSelectedBrand("all");
    setSelectedCategory("all");
    setSelectedRangeName("all");
    setSelectedFormat("all");
    setSelectedPackaging("all");
    setSelectedProductVariantId("all");
    setSelectedCountry("all");
    setSelectedWebsite("all");
    setSelectedStore("all");
    setSelectedCurrency("all");
    setSelectedStatus("all");
    setPriceMode("average");
    setSelectedWeek("");
    setTimeView("latest");
    setPage(1);
  };

  const productOptions = useMemo(() => filters?.products || [], [filters]);
  const brandOptions = useMemo(
    () => uniqueSorted(productOptions.map((product) => product.brand)),
    [productOptions],
  );
  const brandScopedProducts = useMemo(
    () => (
      selectedBrand === "all"
        ? productOptions
        : productOptions.filter((product) => product.brand === selectedBrand)
    ),
    [productOptions, selectedBrand],
  );
  const categoryOptions = useMemo(
    () => uniqueSorted(brandScopedProducts.map((product) => product.category)),
    [brandScopedProducts],
  );
  const categoryScopedProducts = useMemo(
    () => (
      selectedCategory === "all"
        ? brandScopedProducts
        : brandScopedProducts.filter((product) => product.category === selectedCategory)
    ),
    [brandScopedProducts, selectedCategory],
  );
  const rangeOptions = useMemo(
    () => uniqueSorted(categoryScopedProducts.map((product) => product.rangeName)),
    [categoryScopedProducts],
  );
  const rangeScopedProducts = useMemo(
    () => (
      selectedRangeName === "all"
        ? categoryScopedProducts
        : categoryScopedProducts.filter((product) => product.rangeName === selectedRangeName)
    ),
    [categoryScopedProducts, selectedRangeName],
  );
  const formatOptions = useMemo(
    () => uniqueSorted(rangeScopedProducts.map((product) => product.format)),
    [rangeScopedProducts],
  );
  const formatScopedProducts = useMemo(
    () => (
      selectedFormat === "all"
        ? rangeScopedProducts
        : rangeScopedProducts.filter((product) => product.format === selectedFormat)
    ),
    [rangeScopedProducts, selectedFormat],
  );
  const packagingOptions = useMemo(
    () => uniqueSorted(formatScopedProducts.map((product) => product.packaging)),
    [formatScopedProducts],
  );
  const productCandidates = useMemo(
    () => (
      selectedPackaging === "all"
        ? formatScopedProducts
        : formatScopedProducts.filter((product) => product.packaging === selectedPackaging)
    ),
    [formatScopedProducts, selectedPackaging],
  );
  const productCandidateIds = useMemo(
    () => new Set(productCandidates.map((product) => product.productVariantId)),
    [productCandidates],
  );
  const productFilterOptions = useMemo(
    () => productCandidates.map((product) => ({ value: String(product.productVariantId), label: product.label })),
    [productCandidates],
  );
  const selectedProductIdNumber = selectedProductVariantId === "all" ? null : Number(selectedProductVariantId);

  useEffect(() => {
    if (selectedBrand !== "all" && !brandOptions.includes(selectedBrand)) setSelectedBrand("all");
  }, [brandOptions, selectedBrand]);

  useEffect(() => {
    if (selectedCategory !== "all" && !categoryOptions.includes(selectedCategory)) setSelectedCategory("all");
  }, [categoryOptions, selectedCategory]);

  useEffect(() => {
    if (selectedRangeName !== "all" && !rangeOptions.includes(selectedRangeName)) setSelectedRangeName("all");
  }, [rangeOptions, selectedRangeName]);

  useEffect(() => {
    if (selectedFormat !== "all" && !formatOptions.includes(selectedFormat)) setSelectedFormat("all");
  }, [formatOptions, selectedFormat]);

  useEffect(() => {
    if (selectedPackaging !== "all" && !packagingOptions.includes(selectedPackaging)) setSelectedPackaging("all");
  }, [packagingOptions, selectedPackaging]);

  useEffect(() => {
    if (selectedProductVariantId === "all") return;
    const exists = productCandidates.some(
      (product) => String(product.productVariantId) === selectedProductVariantId,
    );
    if (!exists) setSelectedProductVariantId("all");
  }, [productCandidates, selectedProductVariantId]);

  const productScope = useMemo(() => {
    let rows = allWeeksData.filter((row) => productCandidateIds.has(row.productVariantId));
    if (selectedProductIdNumber !== null) {
      rows = rows.filter((row) => row.productVariantId === selectedProductIdNumber);
    }
    return rows;
  }, [allWeeksData, productCandidateIds, selectedProductIdNumber]);

  const countries = useMemo(
    () => [...new Set(productScope.map((row) => row.country).filter(Boolean) as string[])].sort(),
    [productScope],
  );

  const countryScope = useMemo(
    () => (selectedCountry === "all" ? productScope : productScope.filter((row) => row.country === selectedCountry)),
    [productScope, selectedCountry],
  );

  const websitesList = useMemo(() => [...new Set(countryScope.map((row) => row.website))].sort(), [countryScope]);

  const websiteScope = useMemo(
    () => (selectedWebsite === "all" ? countryScope : countryScope.filter((row) => row.website === selectedWebsite)),
    [countryScope, selectedWebsite],
  );

  const storesList = useMemo(() => [...new Set(websiteScope.map((row) => row.store))].sort(), [websiteScope]);

  const storeScope = useMemo(
    () => (selectedStore === "all" ? websiteScope : websiteScope.filter((row) => row.store === selectedStore)),
    [websiteScope, selectedStore],
  );

  const currenciesList = useMemo(() => [...new Set(storeScope.map((row) => row.currency))].sort(), [storeScope]);

  const currencyScope = useMemo(
    () => (selectedCurrency === "all" ? storeScope : storeScope.filter((row) => row.currency === selectedCurrency)),
    [storeScope, selectedCurrency],
  );

  const statusScope = useMemo(
    () =>
      selectedStatus === "all"
        ? currencyScope
        : currencyScope.filter((row) => normalizeStatus(row.dataStatus) === selectedStatus),
    [currencyScope, selectedStatus],
  );

  const availableWeeks = useMemo(
    () => [...new Set(statusScope.map((row) => row.weekStart))].sort().reverse(),
    [statusScope],
  );

  const weekOptions = useMemo(() => {
    if (timeView !== "specific") {
      return [{ value: NO_WEEK_OPTION, label: "Enable Specific Week mode" }];
    }

    if (!availableWeeks.length) {
      return [{ value: NO_WEEK_OPTION, label: "No weeks for this scope" }];
    }

    return availableWeeks.map((week) => ({ value: week, label: formatWeekLabel(week) }));
  }, [timeView, availableWeeks]);

  useEffect(() => {
    if (selectedCountry !== "all" && !countries.includes(selectedCountry)) setSelectedCountry("all");
  }, [countries, selectedCountry]);

  useEffect(() => {
    if (selectedWebsite !== "all" && !websitesList.includes(selectedWebsite)) setSelectedWebsite("all");
  }, [websitesList, selectedWebsite]);

  useEffect(() => {
    if (selectedStore !== "all" && !storesList.includes(selectedStore)) setSelectedStore("all");
  }, [storesList, selectedStore]);

  useEffect(() => {
    if (selectedCurrency !== "all" && !currenciesList.includes(selectedCurrency)) setSelectedCurrency("all");
  }, [currenciesList, selectedCurrency]);

  useEffect(() => {
    if (timeView !== "specific") return;

    if (!availableWeeks.length) {
      if (selectedWeek) setSelectedWeek("");
      return;
    }

    if (!selectedWeek || !availableWeeks.includes(selectedWeek)) {
      setSelectedWeek(availableWeeks[0]);
    }
  }, [timeView, availableWeeks, selectedWeek]);

  const filtered = useMemo(() => {
    let rows = summaryRows.filter((row) => productCandidateIds.has(row.productVariantId));

    if (selectedProductIdNumber !== null) {
      rows = rows.filter((row) => row.productVariantId === selectedProductIdNumber);
    }
    if (selectedCountry !== "all") rows = rows.filter((row) => row.country === selectedCountry);
    if (selectedWebsite !== "all") rows = rows.filter((row) => row.website === selectedWebsite);
    if (selectedStore !== "all") rows = rows.filter((row) => row.store === selectedStore);
    if (selectedCurrency !== "all") rows = rows.filter((row) => row.currency === selectedCurrency);
    if (selectedStatus !== "all") rows = rows.filter((row) => normalizeStatus(row.dataStatus) === selectedStatus);

    return rows;
  }, [
    summaryRows,
    productCandidateIds,
    selectedProductIdNumber,
    selectedCountry,
    selectedWebsite,
    selectedStore,
    selectedCurrency,
    selectedStatus,
  ]);

  const sortedFiltered = useMemo(
    () =>
      [...filtered].sort(
        (a, b) =>
          b.weekStart.localeCompare(a.weekStart) ||
          (a.priceEur ?? Number.POSITIVE_INFINITY) - (b.priceEur ?? Number.POSITIVE_INFINITY),
      ),
    [filtered],
  );

  const totalPages = Math.max(1, Math.ceil(sortedFiltered.length / pageSize));

  useEffect(() => {
    setPage(1);
  }, [
    selectedBrand,
    selectedCategory,
    selectedRangeName,
    selectedFormat,
    selectedPackaging,
    selectedProductVariantId,
    selectedCountry,
    selectedWebsite,
    selectedStore,
    selectedCurrency,
    selectedStatus,
    priceMode,
    selectedWeek,
    timeView,
  ]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const displayedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedFiltered.slice(start, start + pageSize);
  }, [sortedFiltered, page]);

  const pageStart = sortedFiltered.length === 0 ? 0 : (page - 1) * pageSize + 1;
  const pageEnd = Math.min(page * pageSize, sortedFiltered.length);

  const unitLabel = useMemo(
    () => sortedFiltered.find((row) => row.unitLabel)?.unitLabel || "EUR/L",
    [sortedFiltered],
  );

  const weekSelectValue = timeView === "specific" && selectedWeek ? selectedWeek : NO_WEEK_OPTION;
  const localPriceHeader = priceMode === "average" ? "Local Avg" : "Local Last";
  const eurPriceHeader = priceMode === "average" ? "EUR Avg" : "EUR Last";

  return (
    <div>
      <PageHeader
        icon={Tag}
        title="Price Records"
        subtitle="Browse retail price records with filters, time view, and listing status."
      />

      {/* Compact Filter Bar */}
      <div className="glass-card rounded-2xl p-3 mb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Active Filter Summary */}
          <div className="flex flex-wrap items-center gap-2">
            <FilterBadge
              icon={Tag}
              label={selectedProductVariantId !== "all" ? "Product" : selectedBrand !== "all" ? "Brand" : "Products"}
              value={selectedProductVariantId !== "all"
                ? productFilterOptions.find(p => p.value === selectedProductVariantId)?.label || "Selected"
                : selectedBrand !== "all" ? selectedBrand : "All"}
              onClear={selectedProductVariantId !== "all" ? () => setSelectedProductVariantId("all") : selectedBrand !== "all" ? () => setSelectedBrand("all") : undefined}
            />
            <FilterBadge
              icon={selectedCountry !== "all" ? undefined : undefined}
              label="Location"
              value={selectedStore !== "all" ? selectedStore : selectedWebsite !== "all" ? selectedWebsite : selectedCountry !== "all" ? selectedCountry : "All"}
              onClear={selectedStore !== "all" ? () => setSelectedStore("all") : selectedWebsite !== "all" ? () => setSelectedWebsite("all") : selectedCountry !== "all" ? () => setSelectedCountry("all") : undefined}
            />
            <FilterBadge
              label="Time"
              value={timeView === "specific" && selectedWeek ? formatWeekLabel(selectedWeek).split(" to ")[0] : timeView === "all" ? "All Weeks" : "Latest"}
            />
            <FilterBadge
              label="Price"
              value={priceMode === "average" ? "Weekly Avg" : "Last Scraped"}
            />
            {selectedStatus !== "all" && (
              <FilterBadge
                label="Status"
                value={selectedStatus === "OK" ? "Listed" : selectedStatus === "PARTIAL" ? "Partial" : "Missing"}
                onClear={() => setSelectedStatus("all")}
                accent="warning"
              />
            )}
          </div>

          {/* Filter Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-8 rounded-lg text-xs"
              onClick={() => setShowFilters(!showFilters)}
            >
              <SlidersHorizontal className="w-3.5 h-3.5 mr-1.5" />
              {showFilters ? "Hide Filters" : "Filters"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 rounded-lg text-xs border-[hsl(var(--cho-teal))]/30 text-[hsl(var(--cho-teal))] hover:bg-[hsl(var(--cho-teal))/0.08]"
              onClick={exportToExcel}
              disabled={!sortedFiltered.length}
            >
              <FileDown className="w-3.5 h-3.5 mr-1.5" /> Export
            </Button>
            <Button variant="ghost" size="sm" className="h-8 rounded-lg text-xs" onClick={resetFilters}>
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Reset
            </Button>
          </div>
        </div>

        {/* Collapsible Filter Panel */}
        {showFilters && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 pt-3 border-t border-border/40"
          >
            {/* Product Filters */}
            <div className="mb-3">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-2">Product Filters</p>
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2">
                <CompactFilterSelect label="Brand" value={selectedBrand} onChange={setSelectedBrand} options={brandOptions} allLabel="All Brands" />
                <CompactFilterSelect label="Category" value={selectedCategory} onChange={setSelectedCategory} options={categoryOptions} allLabel="All Categories" />
                <CompactFilterSelect label="Range" value={selectedRangeName} onChange={setSelectedRangeName} options={rangeOptions} allLabel="All Ranges" />
                <CompactFilterSelect label="Format" value={selectedFormat} onChange={setSelectedFormat} options={formatOptions} allLabel="All Formats" />
                <CompactFilterSelect label="Packaging" value={selectedPackaging} onChange={setSelectedPackaging} options={packagingOptions} allLabel="All Packagings" />
                <CompactFilterSelect
                  label="Product"
                  value={selectedProductVariantId}
                  onChange={setSelectedProductVariantId}
                  options={[]}
                  allLabel=""
                  customOptions={[{ value: "all", label: "All Products" }, ...productFilterOptions]}
                  disabled={productFilterOptions.length === 0}
                />
              </div>
            </div>

            {/* Location & Other Filters */}
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-2">Location & Settings</p>
              <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-2">
                <CompactFilterSelect label="Country" value={selectedCountry} onChange={setSelectedCountry} options={countries} allLabel="All Countries" />
                <CompactFilterSelect label="Website" value={selectedWebsite} onChange={setSelectedWebsite} options={websitesList} allLabel="All Websites" />
                <CompactFilterSelect label="Store" value={selectedStore} onChange={setSelectedStore} options={storesList} allLabel="All Stores" />
                <CompactFilterSelect label="Currency" value={selectedCurrency} onChange={setSelectedCurrency} options={currenciesList} allLabel="All Currencies" />
                <CompactFilterSelect
                  label="Listing"
                  value={selectedStatus}
                  onChange={(value) => setSelectedStatus(value as StatusFilter)}
                  options={[]}
                  allLabel=""
                  customOptions={[
                    { value: "all", label: "All" },
                    { value: "OK", label: "Listed" },
                    { value: "PARTIAL", label: "Partial" },
                    { value: "MISSING", label: "Not listed" },
                  ]}
                />
                <CompactFilterSelect
                  label="Price Basis"
                  value={priceMode}
                  onChange={(value) => setPriceMode(value as PriceMode)}
                  options={[]}
                  allLabel=""
                  customOptions={[
                    { value: "average", label: "Weekly Avg" },
                    { value: "last_scraped", label: "Last Scraped" },
                  ]}
                />
                <CompactFilterSelect
                  label="Time View"
                  value={timeView}
                  onChange={(value) => setTimeView(value as TimeViewMode)}
                  options={[]}
                  allLabel=""
                  customOptions={[
                    { value: "latest", label: "Latest Week" },
                    { value: "specific", label: "Specific Week" },
                    { value: "all", label: "All Weeks" },
                  ]}
                />
                <CompactFilterSelect
                  label="Week"
                  value={weekSelectValue}
                  onChange={(value) => {
                    if (value !== NO_WEEK_OPTION) setSelectedWeek(value);
                  }}
                  options={[]}
                  allLabel=""
                  customOptions={weekOptions}
                  disabled={timeView !== "specific" || !availableWeeks.length}
                />
              </div>
            </div>
          </motion.div>
        )}
      </div>

      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="overflow-auto max-h-[500px]">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/30 hover:bg-muted/30">
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Product</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Country</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Store</TableHead>
                  <TableHead className="text-right font-bold text-xs uppercase tracking-wider">{localPriceHeader}</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Curr.</TableHead>
                  <TableHead className="text-right font-bold text-xs uppercase tracking-wider">{eurPriceHeader}</TableHead>
                  <TableHead className="text-right font-bold text-xs uppercase tracking-wider">Unit</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Listing</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Link</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Screenshot</TableHead>
                  <TableHead className="font-bold text-xs uppercase tracking-wider">Week</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayedRows.map((row, index) => (
                  <TableRow key={`${row.productVariantId}-${row.store}-${row.weekStart}-${index}`} className="hover:bg-muted/20 transition-colors">
                    <TableCell className="text-sm">
                      <div className="font-semibold">{row.brand}</div>
                      <div className="text-xs text-muted-foreground">
                        {[row.category, row.rangeName].filter(Boolean).join(" ")} - {row.variantLabel}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{row.country}</TableCell>
                    <TableCell className="text-sm">{row.store}</TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {row.price === null
                        ? "-"
                        : priceMode === "last_scraped" &&
                            row.basePrice !== null &&
                            row.basePrice > 0 &&
                            row.price < row.basePrice
                          ? (
                              <div className="flex flex-col items-end leading-tight">
                                <span className="font-semibold">{row.price.toFixed(2)}</span>
                                <span className="text-xs text-muted-foreground line-through">
                                  {row.basePrice.toFixed(2)}
                                </span>
                                <span className="text-[11px] text-muted-foreground font-medium">
                                  -{(((row.basePrice - row.price) / row.basePrice) * 100).toFixed(0)}%
                                </span>
                              </div>
                            )
                          : row.price.toFixed(2)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground font-medium">{row.currency}</TableCell>
                    <TableCell className="text-right font-bold text-sm tabular-nums text-primary">
                      {row.priceEur === null ? "-" : `€${row.priceEur.toFixed(2)}`}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums">
                      {row.unitPriceEur === null ? "-" : `${row.unitLabel || "EUR/L"} ${row.unitPriceEur.toFixed(2)}`}
                    </TableCell>
                    <TableCell className="text-xs font-semibold">
                      <span className={`inline-flex rounded-full px-2 py-1 ${statusBadgeClass(row.dataStatus)}`}>
                        {statusLabel(row.dataStatus)}
                      </span>
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

function FilterBadge({
  icon: Icon,
  label,
  value,
  onClear,
  accent,
}: {
  icon?: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  onClear?: () => void;
  accent?: "warning";
}) {
  return (
    <div className={cn(
      "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs",
      accent === "warning"
        ? "border-amber-500/30 bg-amber-500/10"
        : "border-border/60 bg-background/80"
    )}>
      {Icon && <Icon className={cn("h-3 w-3", accent === "warning" ? "text-amber-500" : "text-muted-foreground")} />}
      <span className={cn("text-muted-foreground", accent === "warning" && "text-amber-600")}>{label}:</span>
      <span className={cn("font-medium max-w-[120px] truncate", accent === "warning" ? "text-amber-700" : "text-foreground")}>
        {value}
      </span>
      {onClear && (
        <button
          onClick={onClear}
          className={cn(
            "ml-1 rounded-full p-0.5 transition-colors",
            accent === "warning"
              ? "text-amber-500 hover:bg-amber-500/20 hover:text-amber-700"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

function CompactFilterSelect({
  label,
  value,
  onChange,
  options,
  allLabel,
  customOptions,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  allLabel: string;
  customOptions?: { value: string; label: string }[];
  disabled?: boolean;
}) {
  return (
    <div>
      <label className="text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">{label}</label>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="h-8 text-xs rounded-lg bg-background/65 border-border/55" disabled={disabled}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {customOptions ? (
            customOptions.map((option) => (
              <SelectItem key={option.value} value={option.value} className="text-xs">
                {option.label}
              </SelectItem>
            ))
          ) : (
            <>
              <SelectItem value="all" className="text-xs">{allLabel}</SelectItem>
              {options.map((option) => (
                <SelectItem key={option} value={option} className="text-xs">{option}</SelectItem>
              ))}
            </>
          )}
        </SelectContent>
      </Select>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
  allLabel,
  customOptions,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  allLabel: string;
  customOptions?: { value: string; label: string }[];
  disabled?: boolean;
}) {
  return (
    <div>
      <label className="text-[9px] font-bold text-muted-foreground uppercase tracking-[0.14em] mb-1 block">{label}</label>
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className="h-9 text-[13px] rounded-xl bg-background/65 border-border/55" disabled={disabled}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {customOptions ? (
            customOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))
          ) : (
            <>
              <SelectItem value="all">{allLabel}</SelectItem>
              {options.map((option) => (
                <SelectItem key={option} value={option}>
                  {option}
                </SelectItem>
              ))}
            </>
          )}
        </SelectContent>
      </Select>
    </div>
  );
}

function formatWeekLabel(weekStart: string): string {
  const parts = weekStart.split("-").map((value) => Number(value));
  if (parts.length !== 3 || parts.some(Number.isNaN)) return weekStart;

  const [year, month, day] = parts;
  const start = new Date(Date.UTC(year, month - 1, day));
  const end = new Date(start);
  end.setUTCDate(start.getUTCDate() + 6);

  const startIso = start.toISOString().slice(0, 10);
  const endIso = end.toISOString().slice(0, 10);
  return `${startIso} to ${endIso}`;
}

function statusLabel(status: string): string {
  const normalized = normalizeStatus(status);
  if (normalized === "MISSING") return "Not listed";
  if (normalized === "PARTIAL") return "Partially listed";
  if (normalized === "OK") return "Listed";
  return normalized || "-";
}

function statusBadgeClass(status: string): string {
  const normalized = normalizeStatus(status);
  if (normalized === "MISSING") return "bg-destructive/15 text-destructive border border-destructive/30";
  if (normalized === "PARTIAL") return "bg-accent/15 text-accent border border-accent/30";
  return "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
}

function normalizeStatus(status: string | null | undefined): string {
  if (!status) return "";
  return status.trim().toUpperCase();
}
