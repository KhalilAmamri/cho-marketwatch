import { useEffect, useMemo, useState } from "react";
import {
  Tag, TrendingUp, Puzzle, Link2, Users, LogOut, ChevronRight, Activity, MapPinned, Building2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import choLogo from "@/assets/cho-group-logo.png";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { getOperationalVisibility, type OperationalFailedRow } from "@/lib/api";
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
  SidebarFooter, SidebarHeader, useSidebar,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const ALERT_ACK_STORAGE_KEY = "cho_ops_acknowledged_alerts_v1";
const ALERT_ACK_CHANGE_EVENT = "cho-ops-alert-ack-changed";

type AlertAcknowledgementMap = Record<string, string>;

function loadAlertAcknowledgements(): AlertAcknowledgementMap {
  if (typeof window === "undefined") return {};

  try {
    const raw = window.localStorage.getItem(ALERT_ACK_STORAGE_KEY);
    if (!raw) return {};

    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};

    const acknowledgements: AlertAcknowledgementMap = {};
    for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
      if (typeof value === "string") acknowledgements[key] = value;
    }

    return acknowledgements;
  } catch {
    return {};
  }
}

function buildAlertKey(row: OperationalFailedRow): string {
  const storeName = (row.storeName || "unknown-store").trim().toLowerCase();
  const errorMessage = (row.errorMessage || "unknown-error").trim().toLowerCase();
  const httpCode = row.httpStatusCode === null ? "no-http" : String(row.httpStatusCode);
  return `${storeName}|${httpCode}|${errorMessage}`;
}

function toTimestamp(value: string): number {
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function getActiveAlertCount(rows: OperationalFailedRow[], acknowledgements: AlertAcknowledgementMap): number {
  const latestByAlertKey = new Map<string, number>();

  for (const row of rows) {
    const key = buildAlertKey(row);
    const seenMs = toTimestamp(row.scrapedAt);
    const previous = latestByAlertKey.get(key) || 0;
    if (seenMs > previous) latestByAlertKey.set(key, seenMs);
  }

  let count = 0;
  for (const [key, latestSeenMs] of latestByAlertKey.entries()) {
    const acknowledgedSeenAt = acknowledgements[key];
    if (!acknowledgedSeenAt || latestSeenMs > toTimestamp(acknowledgedSeenAt)) {
      count += 1;
    }
  }

  return count;
}

const marketPages = [
  { title: "Price Analytics", url: "/trends", icon: TrendingUp },
  { title: "Price Records", url: "/prices", icon: Tag },
  { title: "Retail Presence", url: "/retail-presence", icon: MapPinned },
];

const adminPages = [
  { title: "Product Management", url: "/admin/products", icon: Puzzle },
  { title: "Scraping URL Management", url: "/admin/urls", icon: Link2 },
  { title: "Stores Management", url: "/admin/stores", icon: Building2 },
  { title: "Pipeline Health & Logs", url: "/admin/operations", icon: Activity },
  { title: "Users", url: "/admin/users", icon: Users },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();
  const { user, isAdmin, logout } = useAuth();
  const [alertAcknowledgements, setAlertAcknowledgements] = useState<AlertAcknowledgementMap>(() => loadAlertAcknowledgements());
  const { data: operationalSummary } = useQuery({
    queryKey: ["operational-visibility", "sidebar-alerts"],
    queryFn: () => getOperationalVisibility(500),
    enabled: isAdmin,
    refetchInterval: 60000,
  });

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === ALERT_ACK_STORAGE_KEY) {
        setAlertAcknowledgements(loadAlertAcknowledgements());
      }
    };

    const onAcknowledgeChanged = () => {
      setAlertAcknowledgements(loadAlertAcknowledgements());
    };

    window.addEventListener("storage", onStorage);
    window.addEventListener(ALERT_ACK_CHANGE_EVENT, onAcknowledgeChanged);

    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(ALERT_ACK_CHANGE_EVENT, onAcknowledgeChanged);
    };
  }, []);

  const isActive = (path: string) => location.pathname === path;
  const operationalAlertCount = useMemo(
    () => (isAdmin
      ? getActiveAlertCount(operationalSummary?.failedRows || [], alertAcknowledgements)
      : 0),
    [isAdmin, operationalSummary?.failedRows, alertAcknowledgements],
  );
  const operationalAlertLabel = operationalAlertCount > 99 ? "99+" : String(operationalAlertCount);
  const navLinkClassName = "group flex items-center gap-3 px-3 py-2.5 rounded-xl border border-transparent text-[13px] font-medium text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/75 transition-colors duration-200";
  const navLinkActiveClassName = "!bg-sidebar-primary/15 !text-sidebar-primary !border-sidebar-primary/35 font-semibold";

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className={cn("pb-3 border-b border-sidebar-border/55", collapsed ? "p-2.5 pt-3" : "p-4")}>
        <div className={cn("flex items-center", collapsed ? "justify-center" : "gap-3")}>
          <div className={cn(
            "rounded-lg overflow-hidden flex-shrink-0 bg-white flex items-center justify-center",
            collapsed ? "w-8 h-8" : "w-10 h-10",
          )}>
            <img src={choLogo} alt="CHO Group" className={cn(collapsed ? "w-7 h-7" : "w-9 h-9", "object-contain")} />
          </div>
          {!collapsed && (
            <div className="overflow-hidden">
              <p className="text-sm font-bold text-sidebar-foreground truncate tracking-tight">CHO MarketWatch</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-sidebar-primary/90">
                Price Intelligence
              </p>
            </div>
          )}
        </div>
      </SidebarHeader>

      {!collapsed && user && (
        <div className="mx-3.5 mt-3 mb-2.5 p-3 rounded-xl border border-sidebar-border/70 bg-sidebar-accent/45">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg gradient-teal flex items-center justify-center text-xs font-bold text-accent-foreground">
              {user.fullName.charAt(0)}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-semibold text-sidebar-foreground truncate">{user.fullName}</p>
              <p className="text-[10px] text-sidebar-foreground/55 uppercase font-bold tracking-[0.14em]">{user.role}</p>
            </div>
          </div>
        </div>
      )}

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] uppercase tracking-[0.18em] font-bold text-sidebar-foreground/45 mb-1">
            Analytics
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {marketPages.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={isActive(item.url)}>
                    <NavLink
                      to={item.url}
                      className={navLinkClassName}
                      activeClassName={navLinkActiveClassName}
                    >
                      <item.icon className="h-4 w-4 flex-shrink-0" />
                      {!collapsed && <span>{item.title}</span>}
                      {!collapsed && isActive(item.url) && (
                        <ChevronRight className="ml-auto h-3.5 w-3.5 text-sidebar-primary/75" />
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {isAdmin && (
          <>
            <Separator className="mx-4 w-auto bg-sidebar-border/65" />
            <SidebarGroup>
              <SidebarGroupLabel className="text-[10px] uppercase tracking-[0.18em] font-bold text-sidebar-foreground/45 mb-1">
                Admin
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {adminPages.map((item) => (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton asChild isActive={isActive(item.url)}>
                        <NavLink
                          to={item.url}
                          className={navLinkClassName}
                          activeClassName={navLinkActiveClassName}
                        >
                          <item.icon className="h-4 w-4 flex-shrink-0" />
                          {!collapsed && <span>{item.title}</span>}
                          {item.url === "/admin/operations" && operationalAlertCount > 0 && (
                            collapsed ? (
                              <span className="ml-auto inline-flex h-2.5 w-2.5 rounded-full bg-destructive" />
                            ) : (
                              <span className="ml-auto inline-flex min-w-5 h-5 items-center justify-center rounded-full border border-destructive/35 bg-destructive/15 text-destructive text-[10px] font-bold px-1.5">
                                {operationalAlertLabel}
                              </span>
                            )
                          )}
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </>
        )}
      </SidebarContent>

      <SidebarFooter className="p-3 pt-2 border-t border-sidebar-border/55">
        {!collapsed && (
          <p className="text-[10px] text-sidebar-foreground/40 mb-2 px-2 font-medium uppercase tracking-[0.12em]">Prices normalized to EUR</p>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-xl border border-transparent text-sm font-medium text-sidebar-foreground/55 hover:text-destructive hover:bg-destructive/10 hover:border-destructive/20 transition-colors duration-200"
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && "Sign out"}
        </button>
      </SidebarFooter>
    </Sidebar>
  );
}
