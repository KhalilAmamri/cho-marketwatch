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

export interface FilterResponse {
  products: string[];
  websites: string[];
  countries: string[];
  currencies: string[];
}

export interface PriceSummaryRow {
  product: string;
  website: string;
  country: string | null;
  store: string;
  currency: string;
  price: number;
  priceEur: number | null;
  sourceUrl: string | null;
  screenshotPath: string | null;
  weekStart: string;
}

export interface TimeseriesRow {
  weekStart: string;
  avgPriceEur: number | null;
  sampleCount: number;
}

export interface ForecastRow {
  date: string;
  pricePred: number;
  priceLow: number | null;
  priceHigh: number | null;
  confidenceLevel: string | null;
  trainingPoints: number | null;
  coverageRate: number | null;
  lastObservedWeek: string | null;
  store: string;
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
  country: string;
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
  createdAt: string | null;
}

export interface ProductFormatPayload {
  brandId: number;
  categoryId: number;
  rangeId: number;
  format: string;
  packaging: string;
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

export async function getOperationalVisibility(limitFailed = 100): Promise<OperationalVisibilityData> {
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
      errorMessage: row.error_message || null,
      screenshotPath: row.screenshot_path || null,
      httpStatusCode: row.http_status_code ?? null,
      scrapedAt: row.scraped_at,
    })),
  };
}

export async function getRetailPresence(country?: string): Promise<RetailPresenceData> {
  const { data } = await api.get("/retail-presence", {
    params: {
      country: country || undefined,
    },
  });

  return {
    country: data.country,
    availableCountries: (data.available_countries || []).map((row: any) => String(row)),
    countryRetailers: Object.fromEntries(
      Object.entries(data.country_retailers || {}).map(([country, retailers]) => [
        String(country),
        Array.isArray(retailers) ? retailers.map((name: any) => String(name)) : [],
      ]),
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

export async function getFilters(): Promise<FilterResponse> {
  const { data } = await api.get("/prices/filters");
  return data;
}

export async function getSummary(weekStart?: string, allWeeks = false): Promise<PriceSummaryRow[]> {
  const params: Record<string, string | boolean> = {};
  if (weekStart) params.week_start = weekStart;
  if (allWeeks) params.all_weeks = true;

  const { data } = await api.get("/prices/summary", {
    params,
  });

  return data.map((row: any) => ({
    product: row.product,
    website: row.website,
    country: row.country,
    store: row.store,
    currency: row.currency,
    price: row.price,
    priceEur: row.price_eur,
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
  product: string,
  website?: string,
  country?: string,
  weeks = 52,
  store?: string,
): Promise<TimeseriesRow[]> {
  const { data } = await api.get("/prices/timeseries", {
    params: {
      product,
      website: website || undefined,
      country: country || undefined,
      store: store || undefined,
      weeks,
    },
  });

  return data.map((row: any) => ({
    weekStart: row.week_start,
    avgPriceEur: row.avg_price_eur,
    sampleCount: row.sample_count,
  }));
}

export async function getForecasts(product: string): Promise<ForecastRow[]> {
  const { data } = await api.get("/forecasts", { params: { product } });
  return data.map((row: any) => ({
    date: row.forecast_date,
    pricePred: row.predicted_price,
    priceLow: row.price_low,
    priceHigh: row.price_high,
    confidenceLevel: row.confidence_level,
    trainingPoints: row.training_points,
    coverageRate: row.coverage_rate ?? null,
    lastObservedWeek: row.last_observed_week ?? null,
    store: row.store,
  }));
}

export async function getAdminLookups(): Promise<AdminLookups> {
  const { data } = await api.get("/admin/lookups");
  return {
    brands: data.brands.map((item: any) => ({ id: item.id, name: item.name })),
    categories: data.categories.map((item: any) => ({ id: item.id, name: item.name })),
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
    productFormats: data.product_formats.map((item: any) => ({ id: item.id, label: item.label })),
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

export async function getStoresAdmin(): Promise<AdminStoreRecord[]> {
  const { data } = await api.get("/admin/stores");
  return data.map(mapAdminStore);
}

export async function getWebsitesAdmin(): Promise<AdminWebsiteRecord[]> {
  const { data } = await api.get("/admin/websites");
  return data.map(mapAdminWebsite);
}

export async function createWebsiteAdmin(payload: AdminWebsitePayload): Promise<AdminWebsiteRecord> {
  const { data } = await api.post("/admin/websites", {
    site_name: payload.siteName,
    base_url: payload.baseUrl,
    country: payload.country,
  });
  return mapAdminWebsite(data);
}

export async function updateWebsiteAdmin(id: number, payload: AdminWebsitePayload): Promise<AdminWebsiteRecord> {
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

export async function createStoreAdmin(payload: AdminStorePayload): Promise<AdminStoreRecord> {
  const { data } = await api.post("/admin/stores", {
    website_id: payload.websiteId,
    store_code: payload.storeCode,
    store_name: payload.storeName,
  });
  return mapAdminStore(data);
}

export async function updateStoreAdmin(id: number, payload: AdminStorePayload): Promise<AdminStoreRecord> {
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

export async function createProductFormatAdmin(payload: ProductFormatPayload): Promise<ProductFormatRecord> {
  const { data } = await api.post("/admin/product-formats", {
    brand_id: payload.brandId,
    category_id: payload.categoryId,
    range_id: payload.rangeId,
    format: payload.format,
    packaging: payload.packaging,
  });
  return mapProductFormat(data);
}

export async function updateProductFormatAdmin(id: number, payload: ProductFormatPayload): Promise<ProductFormatRecord> {
  const { data } = await api.put(`/admin/product-formats/${id}`, {
    brand_id: payload.brandId,
    category_id: payload.categoryId,
    range_id: payload.rangeId,
    format: payload.format,
    packaging: payload.packaging,
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

export async function createProductUrlAdmin(payload: ProductUrlPayload): Promise<ProductUrlRecord> {
  const { data } = await api.post("/admin/product-urls", {
    website_id: payload.websiteId,
    store_id: payload.storeId,
    product_format_id: payload.productFormatId,
    url: payload.url,
    is_active: payload.isActive,
  });
  return mapProductUrl(data);
}

export async function updateProductUrlAdmin(id: number, payload: ProductUrlPayload): Promise<ProductUrlRecord> {
  const { data } = await api.put(`/admin/product-urls/${id}`, {
    website_id: payload.websiteId,
    store_id: payload.storeId,
    product_format_id: payload.productFormatId,
    url: payload.url,
    is_active: payload.isActive,
  });
  return mapProductUrl(data);
}

export async function setProductUrlActiveAdmin(id: number, isActive: boolean): Promise<ProductUrlRecord> {
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

export async function createUserAdmin(payload: AdminUserCreatePayload): Promise<AdminUserRecord> {
  const { data } = await api.post("/admin/users", {
    username: payload.username,
    password: payload.password,
    full_name: payload.fullName,
    role: payload.role,
    is_active: payload.isActive,
  });
  return mapAdminUser(data);
}

export async function updateUserAdmin(id: number, payload: AdminUserUpdatePayload): Promise<AdminUserRecord> {
  const body: Record<string, unknown> = {};
  if (Object.prototype.hasOwnProperty.call(payload, "fullName")) body.full_name = payload.fullName;
  if (Object.prototype.hasOwnProperty.call(payload, "role")) body.role = payload.role;
  if (Object.prototype.hasOwnProperty.call(payload, "isActive")) body.is_active = payload.isActive;

  const { data } = await api.put(`/admin/users/${id}`, body);
  return mapAdminUser(data);
}

export async function setUserActiveAdmin(id: number, isActive: boolean): Promise<AdminUserRecord> {
  const { data } = await api.patch(`/admin/users/${id}/active`, {
    is_active: isActive,
  });
  return mapAdminUser(data);
}

export async function deleteUserAdmin(id: number): Promise<void> {
  await api.delete(`/admin/users/${id}`);
}
