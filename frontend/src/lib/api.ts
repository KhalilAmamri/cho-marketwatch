/* eslint-disable @typescript-eslint/no-explicit-any */
import axios from "axios";

export const TOKEN_STORAGE_KEY = "cho_marketwatch_token";

const defaultApiBaseUrl =
  typeof window !== "undefined"
    ? `http://${window.location.hostname}:8000/api/v1`
    : "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl,
  timeout: 15000,
});

const SCRAPE_ACTION_TIMEOUT_MS = 180000;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    config.headers = (config.headers ?? {}) as any;
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface AuthUser {
  id: number;
  username: string;
  fullName: string;
  role: "admin" | "user";
}

export interface ProductFilterOption {
  productVariantId: number;
  label: string;
  familyLabel: string;
  variantLabel: string;
  brand: string;
  category: string;
  rangeName: string;
  format: string;
  packaging: string;
}

export interface FilterResponse {
  products: ProductFilterOption[];
  websites: string[];
  countries: string[];
  currencies: string[];
}

export type PriceDataStatus = "OK" | "MISSING" | "PARTIAL";
export type PriceMode = "average" | "last_scraped";

export interface PriceSummaryRow {
  productVariantId: number;
  product: string;
  familyLabel: string;
  variantLabel: string;
  brand: string;
  category: string;
  rangeName: string;
  format: string;
  packaging: string;
  website: string;
  country: string | null;
  store: string;
  currency: string;
  price: number | null;
  basePrice: number | null;
  isDiscounted: boolean | null;
  priceEur: number | null;
  unitPriceEur: number | null;
  unitLabel: string | null;
  dataStatus: PriceDataStatus;
  sourceUrl: string | null;
  screenshotPath: string | null;
  weekStart: string;
}

export interface TimeseriesRow {
  weekStart: string;
  avgPriceEur: number | null;
  avgUnitPriceEur: number | null;
  unitLabel: string | null;
  sampleCount: number;
  dataStatus: PriceDataStatus;
}

export interface PriceAnalysisKpis {
  latestWeekStart: string | null;
  products: number;
  stores: number;
  countries: number;
  avgPriceEur: number | null;
  maxPriceEur: number | null;
  minPriceEur: number | null;
  unitLabel: string | null;
}

export interface ClusteredBarRank {
  rank: number;
  store: string;
  country?: string | null;
  unitPriceEur: number | null;
  priceEur?: number | null;
}

export interface ClusteredBarGroup {
  productVariantId: number;
  product: string;
  ranks: ClusteredBarRank[];
}

export interface StoreShareSlice {
  store: string;
  country?: string | null;
  records: number;
}

export interface PriceAnalysisResponse {
  kpis: PriceAnalysisKpis;
  clustered: ClusteredBarGroup[];
  trend: TimeseriesRow[];
  storeShare: StoreShareSlice[];
}

export interface MarketOverviewKpis {
  latestWeekStart: string | null;
  products: number;
  stores: number;
  countries: number;
  avgDiscountPct: number | null;
  avgUnitPriceEur: number | null;
  maxUnitPriceEur: number | null;
  minUnitPriceEur: number | null;
  unitLabel: string | null;
}

export interface StoreUnitRankingRow {
  store: string;
  country?: string | null;
  avgUnitPriceEur: number | null;
  sampleCount: number;
}

export interface StorePresenceSlice {
  store: string;
  country?: string | null;
  records: number;
}

export interface StoreOption {
  store: string;
  country: string | null;
}

export interface MarketOverviewResponse {
  kpis: MarketOverviewKpis;
  storeRankings: StoreUnitRankingRow[];
  storePresence: StorePresenceSlice[];
}

export interface MarketChangeRow {
  productVariantId: number;
  product: string;
  thisWeekUnitPriceEur: number | null;
  lastWeekUnitPriceEur: number | null;
  deltaUnitPriceEur: number | null;
  deltaPct: number | null;
  hasDiscount: boolean;
  screenshotPath: string | null;
  sourceUrl: string | null;
  exampleStore: string | null;
  exampleCountry: string | null;
}

export async function getStoreUniverse(options?: {
  website?: string;
  country?: string;
}): Promise<StoreOption[]> {
  const { data } = await api.get("/prices/stores", {
    params: {
      website: options?.website || undefined,
      country: options?.country || undefined,
    },
  });

  return (data || []).map((row: any) => ({
    store: row.store,
    country: row.country ?? null,
  }));
}

export interface DashboardKpis {
  latestWeekStart: string | null;
  lastRefreshedAt: string | null;
  lastUpdate: string | null;
  productsTracked: number;
  websitesTracked: number;
  storesTracked: number;
  latestWeekRecords: number;
}

export interface OperationalStatusCodeCount {
  statusCode: number;
  count: number;
}

export interface OperationalFailedRow {
  id: number;
  storeName: string;
  productLabel: string;
  errorMessage: string | null;
  screenshotPath: string | null;
  httpStatusCode: number | null;
  scrapedAt: string;
}

export interface OperationalVisibilityData {
  successRate: number;
  totalRecords: number;
  failedRequests: number;
  successRequests: number;
  statusCodeCounts: OperationalStatusCodeCount[];
  failedRows: OperationalFailedRow[];
}

export type OperationStatus = "pending" | "processed" | "failed";

export interface OperationLogRow {
  rawStagingId: number;
  productUrlId: number;
  websiteName: string;
  storeName: string;
  productLabel: string;
  status: OperationStatus;
  httpStatusCode: number | null;
  errorMessage: string | null;
  screenshotPath: string | null;
  scrapedAt: string;
  processedAt: string | null;
}

export interface ScrapeActionData {
  mode: "manual" | "retry";
  message: string;
  retryOfRawId: number | null;
  rawRow: OperationLogRow;
}

export type RetailPresenceStatus = "all_present" | "partial" | "none";

export interface RetailPresenceWebsite {
  websiteId: number;
  siteName: string;
  country: string | null;
}

export interface RetailPresenceCell {
  websiteId: number;
  present: boolean;
}

export interface RetailPresenceFormatRow {
  productFormatId: number;
  format: string;
  packaging: string;
  formatLabel: string;
  presenceStatus: RetailPresenceStatus;
  presentCount: number;
  missingCount: number;
  coverageRate: number;
  cells: RetailPresenceCell[];
}

export interface RetailPresenceProductRow {
  productId: number;
  familyLabel: string;
  presenceStatus: RetailPresenceStatus;
  presentFormats: number;
  totalFormats: number;
  formats: RetailPresenceFormatRow[];
}

export interface RetailPresenceKpis {
  totalProductFamilies: number;
  totalFormats: number;
  totalWebsites: number;
  totalActiveLinks: number;
  totalMatrixCells: number;
  presentCells: number;
  missingCells: number;
  coverageRate: number;
}

export interface RetailPresenceData {
  country: string | null;
  availableCountries: string[];
  countryRetailers: Record<string, string[]>;
  websites: RetailPresenceWebsite[];
  kpis: RetailPresenceKpis;
  rows: RetailPresenceProductRow[];
}

export interface LookupItem {
  id: number;
  name: string;
}

export type ScraperStatus = "active" | "pending";

export interface WebsiteOption {
  id: number;
  siteName: string;
  baseUrl: string;
  country: string;
  scraperStatus: ScraperStatus;
}

export interface StoreOption {
  id: number;
  websiteId: number;
  websiteName: string;
  storeCode: string;
  storeName: string | null;
  label: string;
}

export interface ProductFormatOption {
  id: number;
  label: string;
}

export interface AdminLookups {
  brands: LookupItem[];
  categories: LookupItem[];
  ranges: LookupItem[];
  websites: WebsiteOption[];
  stores: StoreOption[];
  productFormats: ProductFormatOption[];
  formats: string[];
  packagings: string[];
}

export interface ProductFormatRecord {
  id: number;
  productId: number;
  brandId: number;
  brandName: string;
  categoryId: number;
  categoryName: string;
  rangeId: number;
  rangeName: string;
  format: string;
  packaging: string;
  volumeValue: number;
  volumeUnit: string;
  createdAt: string | null;
}

export interface ProductFormatPayload {
  brandId: number;
  categoryId: number;
  rangeId: number;
  format: string;
  packaging: string;
  volumeValue: number;
  volumeUnit: string;
}

export interface ProductUrlRecord {
  id: number;
  websiteId: number;
  websiteName: string;
  country: string | null;
  storeId: number | null;
  storeCode: string | null;
  productFormatId: number;
  productLabel: string;
  url: string;
  isActive: boolean;
  createdAt: string | null;
}

export interface ProductUrlPayload {
  websiteId: number;
  storeId: number | null;
  productFormatId: number;
  url: string;
  isActive: boolean;
}

export interface AdminStoreRecord {
  id: number;
  websiteId: number;
  websiteName: string;
  country: string | null;
  storeCode: string;
  storeName: string | null;
  label: string;
  createdAt: string | null;
}

export interface AdminWebsiteRecord {
  id: number;
  siteName: string;
  baseUrl: string;
  country: string;
  scraperStatus: ScraperStatus;
  createdAt: string | null;
}

export interface AdminWebsitePayload {
  siteName: string;
  baseUrl: string;
  country: string;
}

export interface AdminStorePayload {
  websiteId: number;
  storeCode: string;
  storeName: string | null;
}

export interface AdminUserRecord {
  id: number;
  username: string;
  fullName: string | null;
  role: "admin" | "user";
  isActive: boolean;
  createdAt: string | null;
  lastLogin: string | null;
}

export interface AdminUserCreatePayload {
  username: string;
  password: string;
  fullName: string | null;
  role: "admin" | "user";
  isActive: boolean;
}

export interface AdminUserUpdatePayload {
  fullName?: string | null;
  role?: "admin" | "user";
  isActive?: boolean;
}

function mapProductFormat(row: any): ProductFormatRecord {
  return {
    id: row.id,
    productId: row.product_id,
    brandId: row.brand_id,
    brandName: row.brand_name,
    categoryId: row.category_id,
    categoryName: row.category_name,
    rangeId: row.range_id,
    rangeName: row.range_name,
    format: row.format,
    packaging: row.packaging,
    volumeValue: Number(row.volume_value),
    volumeUnit: String(row.volume_unit || ""),
    createdAt: row.created_at || null,
  };
}

function mapProductUrl(row: any): ProductUrlRecord {
  return {
    id: row.id,
    websiteId: row.website_id,
    websiteName: row.website_name,
    country: row.country,
    storeId: row.store_id,
    storeCode: row.store_code,
    productFormatId: row.product_format_id,
    productLabel: row.product_label,
    url: row.url,
    isActive: row.is_active,
    createdAt: row.created_at || null,
  };
}

function mapAdminStore(row: any): AdminStoreRecord {
  return {
    id: row.id,
    websiteId: row.website_id,
    websiteName: row.website_name,
    country: row.country || null,
    storeCode: row.store_code,
    storeName: row.store_name || null,
    label: row.label,
    createdAt: row.created_at || null,
  };
}

function mapAdminWebsite(row: any): AdminWebsiteRecord {
  return {
    id: row.id,
    siteName: row.site_name,
    baseUrl: String(row.base_url || ""),
    country: String(row.country || ""),
    scraperStatus: row.scraper_status === "active" ? "active" : "pending",
    createdAt: row.created_at || null,
  };
}

function mapAdminUser(row: any): AdminUserRecord {
  return {
    id: row.id,
    username: row.username,
    fullName: row.full_name || null,
    role: row.role,
    isActive: row.is_active,
    createdAt: row.created_at || null,
    lastLogin: row.last_login || null,
  };
}

export async function login(username: string, password: string) {
  const { data } = await api.post("/auth/login", { username, password });
  return {
    accessToken: data.access_token as string,
    user: {
      id: data.user.id,
      username: data.user.username,
      fullName: data.user.full_name || data.user.username,
      role: data.user.role,
    } as AuthUser,
  };
}

export async function me(): Promise<AuthUser> {
  const { data } = await api.get("/auth/me");
  return {
    id: data.id,
    username: data.username,
    fullName: data.full_name || data.username,
    role: data.role,
  };
}

export async function getKpis(): Promise<DashboardKpis> {
  const { data } = await api.get("/prices/kpis");
  return {
    latestWeekStart: data.latest_week_start,
    lastRefreshedAt: data.last_refreshed_at,
    lastUpdate: data.last_update,
    productsTracked: data.products_tracked,
    websitesTracked: data.websites_tracked,
    storesTracked: data.stores_tracked,
    latestWeekRecords: data.latest_week_records,
  };
}

export async function getOperationalVisibility(
  limitFailed = 100,
): Promise<OperationalVisibilityData> {
  const { data } = await api.get("/operations/visibility", {
    params: { limit_failed: limitFailed },
  });

  return {
    successRate: data.success_rate,
    totalRecords: data.total_records,
    failedRequests: data.failed_requests,
    successRequests: data.success_requests,
    statusCodeCounts: (data.status_code_counts || []).map((row: any) => ({
      statusCode: row.status_code,
      count: row.count,
    })),
    failedRows: (data.failed_rows || []).map((row: any) => ({
      id: row.id,
      storeName: row.store_name,
      productLabel: row.product_label,
      errorMessage: row.error_message || null,
      screenshotPath: row.screenshot_path || null,
      httpStatusCode: row.http_status_code ?? null,
      scrapedAt: row.scraped_at,
    })),
  };
}

function mapOperationLogRow(row: any): OperationLogRow {
  return {
    rawStagingId: row.raw_staging_id,
    productUrlId: row.product_url_id,
    websiteName: row.website_name,
    storeName: row.store_name,
    productLabel: row.product_label,
    status: row.status,
    httpStatusCode: row.http_status_code ?? null,
    errorMessage: row.error_message || null,
    screenshotPath: row.screenshot_path || null,
    scrapedAt: row.scraped_at,
    processedAt: row.processed_at || null,
  };
}

function mapScrapeActionData(data: any): ScrapeActionData {
  return {
    mode: data.mode,
    message: data.message,
    retryOfRawId: data.retry_of_raw_id ?? null,
    rawRow: mapOperationLogRow(data.raw_row),
  };
}

export async function getOperationLogs(
  limit = 200,
): Promise<OperationLogRow[]> {
  const { data } = await api.get("/operations/logs", {
    params: { limit },
  });

  return (data.rows || []).map((row: any) => mapOperationLogRow(row));
}

export async function scrapeProductUrlNow(
  productUrlId: number,
  headless = false,
): Promise<ScrapeActionData> {
  const { data } = await api.post(
    `/operations/scrape/product-url/${productUrlId}`,
    null,
    {
      params: { headless },
      timeout: SCRAPE_ACTION_TIMEOUT_MS,
    },
  );
  return mapScrapeActionData(data);
}

export async function retryFailedRawNow(
  rawStagingId: number,
  headless = false,
): Promise<ScrapeActionData> {
  const { data } = await api.post(
    `/operations/retry/raw/${rawStagingId}`,
    null,
    {
      params: { headless },
      timeout: SCRAPE_ACTION_TIMEOUT_MS,
    },
  );
  return mapScrapeActionData(data);
}

export async function getRetailPresence(
  country?: string,
): Promise<RetailPresenceData> {
  const { data } = await api.get("/retail-presence", {
    params: {
      country: country || undefined,
    },
  });

  return {
    country: data.country ?? null,
    availableCountries: (data.available_countries || []).map((row: any) =>
      String(row),
    ),
    countryRetailers: Object.fromEntries(
      Object.entries(data.country_retailers || {}).map(
        ([country, retailers]) => [
          String(country),
          Array.isArray(retailers)
            ? retailers.map((name: any) => String(name))
            : [],
        ],
      ),
    ),
    websites: (data.websites || []).map((row: any) => ({
      websiteId: row.website_id,
      siteName: row.site_name,
      country: row.country || null,
    })),
    kpis: {
      totalProductFamilies: data.kpis?.total_product_families || 0,
      totalFormats: data.kpis?.total_formats || 0,
      totalWebsites: data.kpis?.total_websites || 0,
      totalActiveLinks: data.kpis?.total_active_links || 0,
      totalMatrixCells: data.kpis?.total_matrix_cells || 0,
      presentCells: data.kpis?.present_cells || 0,
      missingCells: data.kpis?.missing_cells || 0,
      coverageRate: data.kpis?.coverage_rate || 0,
    },
    rows: (data.rows || []).map((row: any) => ({
      productId: row.product_id,
      familyLabel: row.family_label,
      presenceStatus: row.presence_status,
      presentFormats: row.present_formats,
      totalFormats: row.total_formats,
      formats: (row.formats || []).map((formatRow: any) => ({
        productFormatId: formatRow.product_format_id,
        format: formatRow.format,
        packaging: formatRow.packaging,
        formatLabel: formatRow.format_label,
        presenceStatus: formatRow.presence_status,
        presentCount: formatRow.present_count,
        missingCount: formatRow.missing_count,
        coverageRate: formatRow.coverage_rate,
        cells: (formatRow.cells || []).map((cell: any) => ({
          websiteId: cell.website_id,
          present: Boolean(cell.present),
        })),
      })),
    })),
  };
}

export type RetailPresenceCountryMetric = {
  country: string;
  iso3: string | null;
  websitesCount: number;
  totalFormats: number;
  presentCells: number;
  totalMatrixCells: number;
  coverageRate: number;
  totalActiveLinks: number;
};

export async function getRetailPresenceCountryMetrics(): Promise<
  RetailPresenceCountryMetric[]
> {
  const { data } = await api.get("/retail-presence/country-metrics");

  return (data || []).map((row: any) => ({
    country: String(row.country),
    iso3: row.iso3 ? String(row.iso3) : null,
    websitesCount: Number(row.websites_count || 0),
    totalFormats: Number(row.total_formats || 0),
    presentCells: Number(row.present_cells || 0),
    totalMatrixCells: Number(row.total_matrix_cells || 0),
    coverageRate: Number(row.coverage_rate || 0),
    totalActiveLinks: Number(row.total_active_links || 0),
  }));
}

export async function getFilters(): Promise<FilterResponse> {
  const { data } = await api.get("/prices/filters");
  return {
    products: (data.products || []).map((row: any) => ({
      productVariantId: row.product_variant_id,
      label: row.label,
      familyLabel: row.family_label,
      variantLabel: row.variant_label,
      brand: row.brand,
      category: row.category,
      rangeName: row.range_name,
      format: row.format,
      packaging: row.packaging,
    })),
    websites: (data.websites || []).map((item: any) => String(item)),
    countries: (data.countries || []).map((item: any) => String(item)),
    currencies: (data.currencies || []).map((item: any) => String(item)),
  };
}

export async function getSummary(
  weekStart?: string,
  allWeeks = false,
  priceMode: PriceMode = "average",
  productVariantId?: number,
  fxBasisWeekStart?: string,
): Promise<PriceSummaryRow[]> {
  const params: Record<string, string | boolean | number> = {
    price_mode: priceMode,
  };
  if (weekStart) params.week_start = weekStart;
  if (fxBasisWeekStart) params.fx_basis_week_start = fxBasisWeekStart;
  if (allWeeks) params.all_weeks = true;
  if (typeof productVariantId === "number")
    params.product_variant_id = productVariantId;

  const { data } = await api.get("/prices/summary", {
    params,
  });

  return data.map((row: any) => ({
    productVariantId: row.product_variant_id,
    product: row.product,
    familyLabel: row.family_label,
    variantLabel: row.variant_label,
    brand: row.brand,
    category: row.category,
    rangeName: row.range_name,
    format: row.format,
    packaging: row.packaging,
    website: row.website,
    country: row.country,
    store: row.store,
    currency: row.currency,
    price: row.price,
    basePrice: row.base_price ?? null,
    isDiscounted: row.is_discounted ?? null,
    priceEur: row.price_eur,
    unitPriceEur: row.unit_price_eur ?? null,
    unitLabel: row.unit_label ?? null,
    dataStatus: row.data_status,
    sourceUrl: row.source_url || null,
    screenshotPath: row.screenshot_path || null,
    weekStart: row.week_start,
  }));
}

export function resolveStorageUrl(storagePath?: string | null): string | null {
  if (!storagePath) return null;
  if (/^https?:\/\//i.test(storagePath)) return storagePath;

  const normalizedPath = String(storagePath).replace(/^\/+/, "");
  const fallbackBase = import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl;
  const apiBase = String(api.defaults.baseURL || fallbackBase);

  try {
    const origin = new URL(apiBase).origin;
    return `${origin}/${normalizedPath}`;
  } catch {
    return `/${normalizedPath}`;
  }
}

export async function getTimeseries(
  productVariantId: number,
  website?: string,
  country?: string,
  weeks = 52,
  store?: string,
  fxBasisWeekStart?: string,
): Promise<TimeseriesRow[]> {
  const { data } = await api.get("/prices/timeseries", {
    params: {
      product_variant_id: productVariantId,
      website: website || undefined,
      country: country || undefined,
      store: store || undefined,
      weeks,
      fx_basis_week_start: fxBasisWeekStart || undefined,
    },
  });

  return data.map((row: any) => ({
    weekStart: row.week_start,
    avgPriceEur: row.avg_price_eur,
    avgUnitPriceEur: row.avg_unit_price_eur ?? null,
    unitLabel: row.unit_label ?? null,
    sampleCount: row.sample_count,
    dataStatus: row.data_status,
  }));
}

export async function getAvailableWeeks(options: {
  website?: string;
  country?: string;
  store?: string;
  limit?: number;
}): Promise<string[]> {
  const { data } = await api.get("/prices/weeks", {
    params: {
      website: options.website || undefined,
      country: options.country || undefined,
      store: options.store || undefined,
      limit: options.limit ?? 260,
    },
  });

  return (data || []).map((value: any) => String(value));
}

export async function getPriceAnalysis(options: {
  productVariantIds?: number[];
  website?: string;
  country?: string;
  weeks?: number;
  fxBasisWeekStart?: string;
}): Promise<PriceAnalysisResponse> {
  const params = new URLSearchParams();

  const ids = (options.productVariantIds || []).filter(
    (id) => Number.isFinite(id) && id > 0,
  );
  for (const id of ids) params.append("product_variant_id", String(id));
  if (options.website) params.append("website", options.website);
  if (options.country) params.append("country", options.country);
  params.append("weeks", String(options.weeks ?? 52));
  if (options.fxBasisWeekStart) params.append("fx_basis_week_start", options.fxBasisWeekStart);

  const { data } = await api.get("/prices/analysis", { params });

  return {
    kpis: {
      latestWeekStart: data.kpis.latest_week_start,
      products: data.kpis.products,
      stores: data.kpis.stores,
      countries: data.kpis.countries,
      avgPriceEur: data.kpis.avg_price_eur ?? null,
      maxPriceEur: data.kpis.max_price_eur ?? null,
      minPriceEur: data.kpis.min_price_eur ?? null,
      unitLabel: data.kpis.unit_label ?? null,
    },
    clustered: (data.clustered || []).map((row: any) => ({
      productVariantId: row.product_variant_id,
      product: row.product,
      ranks: (row.ranks || []).map((rank: any) => ({
        rank: rank.rank,
        store: rank.store,
        country: rank.country ?? null,
        unitPriceEur:
          typeof rank.unit_price_eur === "number" ? rank.unit_price_eur : null,
        priceEur: typeof rank.price_eur === "number" ? rank.price_eur : null,
      })),
    })),
    trend: (data.trend || []).map((row: any) => ({
      weekStart: row.week_start,
      avgPriceEur: row.avg_price_eur ?? null,
      avgUnitPriceEur: row.avg_unit_price_eur ?? null,
      unitLabel: row.unit_label ?? null,
      sampleCount: row.sample_count,
      dataStatus: row.data_status,
    })),
    storeShare: (data.store_share || []).map((row: any) => ({
      store: row.store,
      country: row.country ?? null,
      records: row.records,
    })),
  };
}

export async function getMarketOverview(options: {
  website?: string;
  country?: string;
  store?: string;
  weekStart?: string;
  fxBasisWeekStart?: string;
}): Promise<MarketOverviewResponse> {
  const { data } = await api.get("/prices/market-overview", {
    params: {
      website: options.website || undefined,
      country: options.country || undefined,
      store: options.store || undefined,
      week_start: options.weekStart || undefined,
      fx_basis_week_start: options.fxBasisWeekStart || undefined,
    },
  });

  return {
    kpis: {
      latestWeekStart: data.kpis.latest_week_start,
      products: data.kpis.products,
      stores: data.kpis.stores,
      countries: data.kpis.countries,
      avgDiscountPct: data.kpis.avg_discount_pct ?? null,
      avgUnitPriceEur: data.kpis.avg_unit_price_eur ?? null,
      maxUnitPriceEur: data.kpis.max_unit_price_eur ?? null,
      minUnitPriceEur: data.kpis.min_unit_price_eur ?? null,
      unitLabel: data.kpis.unit_label ?? null,
    },
    storeRankings: (data.store_rankings || []).map((row: any) => ({
      store: row.store,
      country: row.country ?? null,
      avgUnitPriceEur: row.avg_unit_price_eur ?? null,
      sampleCount: row.sample_count,
    })),
    storePresence: (data.store_presence || []).map((row: any) => ({
      store: row.store,
      country: row.country ?? null,
      records: row.records,
    })),
  };
}

export async function getMarketChanges(options: {
  weekStart: string;
  previousWeekStart?: string;
  fxBasisWeekStart?: string;
  website?: string;
  country?: string;
  store?: string;
  limit?: number;
}): Promise<MarketChangeRow[]> {
  const { data } = await api.get("/prices/market-changes", {
    params: {
      week_start: options.weekStart,
      previous_week_start: options.previousWeekStart || undefined,
      fx_basis_week_start: options.fxBasisWeekStart || undefined,
      website: options.website || undefined,
      country: options.country || undefined,
      store: options.store || undefined,
      limit: options.limit ?? 15,
    },
  });

  return (data || []).map((row: any) => ({
    productVariantId: row.product_variant_id,
    product: row.product,
    thisWeekUnitPriceEur:
      typeof row.this_week_unit_price_eur === "number"
        ? row.this_week_unit_price_eur
        : row.this_week_unit_price_eur ?? null,
    lastWeekUnitPriceEur:
      typeof row.last_week_unit_price_eur === "number"
        ? row.last_week_unit_price_eur
        : row.last_week_unit_price_eur ?? null,
    deltaUnitPriceEur:
      typeof row.delta_unit_price_eur === "number"
        ? row.delta_unit_price_eur
        : row.delta_unit_price_eur ?? null,
    deltaPct:
      typeof row.delta_pct === "number" ? row.delta_pct : row.delta_pct ?? null,
    hasDiscount: Boolean(row.has_discount),
    screenshotPath: row.screenshot_path ?? null,
    sourceUrl: row.source_url ?? null,
    exampleStore: row.example_store ?? null,
    exampleCountry: row.example_country ?? null,
  }));
}

export async function getAdminLookups(): Promise<AdminLookups> {
  const { data } = await api.get("/admin/lookups");
  return {
    brands: data.brands.map((item: any) => ({ id: item.id, name: item.name })),
    categories: data.categories.map((item: any) => ({
      id: item.id,
      name: item.name,
    })),
    ranges: data.ranges.map((item: any) => ({ id: item.id, name: item.name })),
    websites: data.websites.map((item: any) => ({
      id: item.id,
      siteName: item.site_name,
      baseUrl: String(item.base_url || ""),
      country: String(item.country || ""),
      scraperStatus: item.scraper_status === "active" ? "active" : "pending",
    })),
    stores: data.stores.map((item: any) => ({
      id: item.id,
      websiteId: item.website_id,
      websiteName: item.website_name,
      storeCode: item.store_code,
      storeName: item.store_name,
      label: item.label,
    })),
    productFormats: data.product_formats.map((item: any) => ({
      id: item.id,
      label: item.label,
    })),
    formats: (data.formats || []).map((item: any) => String(item)),
    packagings: (data.packagings || []).map((item: any) => String(item)),
  };
}

export async function createBrandAdmin(name: string): Promise<LookupItem> {
  const { data } = await api.post("/admin/lookups/brands", { name });
  return { id: data.id, name: data.name };
}

export async function createCategoryAdmin(name: string): Promise<LookupItem> {
  const { data } = await api.post("/admin/lookups/categories", { name });
  return { id: data.id, name: data.name };
}

export async function createRangeAdmin(name: string): Promise<LookupItem> {
  const { data } = await api.post("/admin/lookups/ranges", { name });
  return { id: data.id, name: data.name };
}

export async function createFormatAdmin(payload: {
  name: string;
  volumeValue: number;
  volumeUnit: string;
}): Promise<LookupItem> {
  const { data } = await api.post("/admin/lookups/formats", {
    name: payload.name,
    volume_value: payload.volumeValue,
    volume_unit: payload.volumeUnit,
  });
  return { id: data.id, name: data.name };
}

export async function createPackagingAdmin(name: string): Promise<LookupItem> {
  const { data } = await api.post("/admin/lookups/packagings", { name });
  return { id: data.id, name: data.name };
}

export async function getStoresAdmin(): Promise<AdminStoreRecord[]> {
  const { data } = await api.get("/admin/stores");
  return data.map(mapAdminStore);
}

export async function getWebsitesAdmin(): Promise<AdminWebsiteRecord[]> {
  const { data } = await api.get("/admin/websites");
  return data.map(mapAdminWebsite);
}

export async function createWebsiteAdmin(
  payload: AdminWebsitePayload,
): Promise<AdminWebsiteRecord> {
  const { data } = await api.post("/admin/websites", {
    site_name: payload.siteName,
    base_url: payload.baseUrl,
    country: payload.country,
  });
  return mapAdminWebsite(data);
}

export async function updateWebsiteAdmin(
  id: number,
  payload: AdminWebsitePayload,
): Promise<AdminWebsiteRecord> {
  const { data } = await api.put(`/admin/websites/${id}`, {
    site_name: payload.siteName,
    base_url: payload.baseUrl,
    country: payload.country,
  });
  return mapAdminWebsite(data);
}

export async function deleteWebsiteAdmin(id: number): Promise<void> {
  await api.delete(`/admin/websites/${id}`);
}

export async function createStoreAdmin(
  payload: AdminStorePayload,
): Promise<AdminStoreRecord> {
  const { data } = await api.post("/admin/stores", {
    website_id: payload.websiteId,
    store_code: payload.storeCode,
    store_name: payload.storeName,
  });
  return mapAdminStore(data);
}

export async function updateStoreAdmin(
  id: number,
  payload: AdminStorePayload,
): Promise<AdminStoreRecord> {
  const { data } = await api.put(`/admin/stores/${id}`, {
    website_id: payload.websiteId,
    store_code: payload.storeCode,
    store_name: payload.storeName,
  });
  return mapAdminStore(data);
}

export async function deleteStoreAdmin(id: number): Promise<void> {
  await api.delete(`/admin/stores/${id}`);
}

export async function getProductFormatsAdmin(): Promise<ProductFormatRecord[]> {
  const { data } = await api.get("/admin/product-formats");
  return data.map(mapProductFormat);
}

export async function createProductFormatAdmin(
  payload: ProductFormatPayload,
): Promise<ProductFormatRecord> {
  const { data } = await api.post("/admin/product-formats", {
    brand_id: payload.brandId,
    category_id: payload.categoryId,
    range_id: payload.rangeId,
    format: payload.format,
    packaging: payload.packaging,
    volume_value: payload.volumeValue,
    volume_unit: payload.volumeUnit,
  });
  return mapProductFormat(data);
}

export async function updateProductFormatAdmin(
  id: number,
  payload: ProductFormatPayload,
): Promise<ProductFormatRecord> {
  const { data } = await api.put(`/admin/product-formats/${id}`, {
    brand_id: payload.brandId,
    category_id: payload.categoryId,
    range_id: payload.rangeId,
    format: payload.format,
    packaging: payload.packaging,
    volume_value: payload.volumeValue,
    volume_unit: payload.volumeUnit,
  });
  return mapProductFormat(data);
}

export async function deleteProductFormatAdmin(id: number): Promise<void> {
  await api.delete(`/admin/product-formats/${id}`);
}

export async function getProductUrlsAdmin(): Promise<ProductUrlRecord[]> {
  const { data } = await api.get("/admin/product-urls");
  return data.map(mapProductUrl);
}

export async function createProductUrlAdmin(
  payload: ProductUrlPayload,
): Promise<ProductUrlRecord> {
  const { data } = await api.post("/admin/product-urls", {
    website_id: payload.websiteId,
    store_id: payload.storeId,
    product_format_id: payload.productFormatId,
    url: payload.url,
    is_active: payload.isActive,
  });
  return mapProductUrl(data);
}

export async function updateProductUrlAdmin(
  id: number,
  payload: ProductUrlPayload,
): Promise<ProductUrlRecord> {
  const { data } = await api.put(`/admin/product-urls/${id}`, {
    website_id: payload.websiteId,
    store_id: payload.storeId,
    product_format_id: payload.productFormatId,
    url: payload.url,
    is_active: payload.isActive,
  });
  return mapProductUrl(data);
}

export async function setProductUrlActiveAdmin(
  id: number,
  isActive: boolean,
): Promise<ProductUrlRecord> {
  const { data } = await api.patch(`/admin/product-urls/${id}/active`, {
    is_active: isActive,
  });
  return mapProductUrl(data);
}

export async function deleteProductUrlAdmin(id: number): Promise<void> {
  await api.delete(`/admin/product-urls/${id}`);
}

export async function getUsersAdmin(): Promise<AdminUserRecord[]> {
  const { data } = await api.get("/admin/users");
  return data.map(mapAdminUser);
}

export async function createUserAdmin(
  payload: AdminUserCreatePayload,
): Promise<AdminUserRecord> {
  const { data } = await api.post("/admin/users", {
    username: payload.username,
    password: payload.password,
    full_name: payload.fullName,
    role: payload.role,
    is_active: payload.isActive,
  });
  return mapAdminUser(data);
}

export async function updateUserAdmin(
  id: number,
  payload: AdminUserUpdatePayload,
): Promise<AdminUserRecord> {
  const body: Record<string, unknown> = {};
  if (Object.prototype.hasOwnProperty.call(payload, "fullName"))
    body.full_name = payload.fullName;
  if (Object.prototype.hasOwnProperty.call(payload, "role"))
    body.role = payload.role;
  if (Object.prototype.hasOwnProperty.call(payload, "isActive"))
    body.is_active = payload.isActive;

  const { data } = await api.put(`/admin/users/${id}`, body);
  return mapAdminUser(data);
}

export async function setUserActiveAdmin(
  id: number,
  isActive: boolean,
): Promise<AdminUserRecord> {
  const { data } = await api.patch(`/admin/users/${id}/active`, {
    is_active: isActive,
  });
  return mapAdminUser(data);
}

export async function deleteUserAdmin(id: number): Promise<void> {
  await api.delete(`/admin/users/${id}`);
}

export interface Country {
  name: string;
  alpha2: string;
  alpha3: string;
}

export async function getCountriesAdmin(): Promise<Country[]> {
  const { data } = await api.get("/admin/countries");
  return (data || []).map((item: any) => ({
    name: String(item.name || ""),
    alpha2: String(item.alpha2 || ""),
    alpha3: String(item.alpha3 || ""),
  }));
}
