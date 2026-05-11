import { Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { getKpis } from "@/lib/api";

type RouteMeta = {
  section: string;
  title: string;
};

const DEFAULT_ROUTE_META: RouteMeta = {
  section: "Dashboard",
  title: "Overview",
};

function getRouteMeta(pathname: string): RouteMeta {
  if (pathname === "/dashboard") {
    return { section: "Overview", title: "Dashboard Home" };
  }
  if (pathname === "/prices") {
    return { section: "Analytics", title: "Price Records" };
  }
  if (pathname === "/trends" || pathname === "/comparison") {
    return { section: "Analytics", title: "Price Analytics" };
  }
  if (pathname === "/retail-presence") {
    return { section: "Analytics", title: "Retail Presence" };
  }
  if (pathname === "/admin/products") {
    return { section: "Admin", title: "Product Management" };
  }
  if (pathname === "/admin/urls") {
    return { section: "Admin", title: "Scraping URL Management" };
  }
  if (pathname === "/admin/stores") {
    return { section: "Admin", title: "Stores Management" };
  }
  if (pathname === "/admin/operations") {
    return { section: "Admin", title: "Pipeline Health & Logs" };
  }
  if (pathname === "/admin/users") {
    return { section: "Admin", title: "Users" };
  }
  return DEFAULT_ROUTE_META;
}

export function DashboardLayout() {
  const location = useLocation();
  const { data: kpis } = useQuery({ queryKey: ["kpis"], queryFn: getKpis });
  const latestWeekStart = kpis?.latestWeekStart || kpis?.lastUpdate || null;
  const lastRefreshedAt = kpis?.lastRefreshedAt || null;
  const latestWeekLabel = latestWeekStart ? new Date(latestWeekStart).toLocaleDateString() : "-";
  const lastRefreshedLabel = lastRefreshedAt ? new Date(lastRefreshedAt).toLocaleString() : "-";
  const routeMeta = getRouteMeta(location.pathname);

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="sticky top-0 z-20 border-b border-border/70 bg-background/80 backdrop-blur-xl">
            <div className="h-[68px] px-4 lg:px-8 flex items-center gap-4">
              <SidebarTrigger className="h-9 w-9 rounded-xl border border-border/70 bg-background/70 text-muted-foreground hover:bg-card hover:text-foreground" />

              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-muted-foreground">{routeMeta.section}</p>
                <p className="text-sm md:text-base font-semibold text-foreground truncate">{routeMeta.title}</p>
              </div>

              <div className="ml-auto hidden xl:flex items-center gap-2">
                <span className="inline-flex items-center rounded-full border border-border/80 bg-card px-2.5 py-1 text-[11px] font-semibold text-muted-foreground">
                  Latest week {latestWeekLabel}
                </span>
                <span className="inline-flex items-center rounded-full border border-border/80 bg-card px-2.5 py-1 text-[11px] font-semibold text-muted-foreground">
                  Last refresh {lastRefreshedLabel}
                </span>
              </div>
            </div>
          </header>

          <main className="flex-1 overflow-auto dashboard-canvas">
            <div className="p-4 md:p-6 lg:p-8">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}
