import { Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { AlertTriangle } from "lucide-react";
import { getKpis, getOperationalVisibility, resolveStorageUrl } from "@/lib/api";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";

export function DashboardLayout() {
  const [alertsOpen, setAlertsOpen] = useState(false);
  const { isAdmin } = useAuth();
  const { data: kpis } = useQuery({ queryKey: ["kpis"], queryFn: getKpis });
  const { data: operational } = useQuery({
    queryKey: ["operational-visibility", "header"],
    queryFn: () => getOperationalVisibility(5),
    enabled: isAdmin,
    refetchInterval: 60000,
  });

  const failedScrapes = isAdmin ? (operational?.failedRows || []) : [];
  const latestWeekStart = kpis?.latestWeekStart || kpis?.lastUpdate || null;
  const lastRefreshedAt = kpis?.lastRefreshedAt || null;
  const latestWeekLabel = latestWeekStart ? new Date(latestWeekStart).toLocaleDateString() : "-";
  const lastRefreshedLabel = lastRefreshedAt ? new Date(lastRefreshedAt).toLocaleString() : "-";

  useEffect(() => {
    if (!isAdmin || failedScrapes.length === 0) {
      setAlertsOpen(false);
    }
  }, [isAdmin, failedScrapes.length]);

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-16 flex items-center gap-4 border-b border-border/50 bg-background/80 backdrop-blur-xl px-6 sticky top-0 z-10">
            <SidebarTrigger className="flex-shrink-0 text-muted-foreground hover:text-foreground" />
            
            <div className="flex-1" />

            {isAdmin && failedScrapes.length > 0 && (
              <button
                onClick={() => setAlertsOpen(!alertsOpen)}
                className="flex items-center gap-2 text-xs font-semibold text-primary bg-primary/10 px-4 py-2 rounded-full border border-primary/20 hover:bg-primary/15 transition-all duration-200"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                {failedScrapes.length} alert{failedScrapes.length > 1 ? "s" : ""}
              </button>
            )}

            <div className="text-xs text-muted-foreground font-medium">
              Latest week: {latestWeekLabel} | Last refreshed: {lastRefreshedLabel}
            </div>
          </header>

          {isAdmin && alertsOpen && failedScrapes.length > 0 && (
            <div className="bg-primary/5 border-b border-primary/10 p-4 space-y-2 animate-fade-in">
              {failedScrapes.map((f, i) => (
                <div key={i} className="text-sm text-foreground glass-card rounded-xl p-4">
                  <span className="font-bold">{f.storeName}</span>
                  <span className="text-muted-foreground"> · HTTP {f.httpStatusCode ?? "-"}</span>
                  <br />
                  <span className="text-xs text-destructive font-medium">{f.errorMessage || "Unknown scrape error"}</span>
                  {f.screenshotPath && resolveStorageUrl(f.screenshotPath) && (
                    <>
                      <br />
                      <a
                        href={resolveStorageUrl(f.screenshotPath) || undefined}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary underline underline-offset-2"
                      >
                        View screenshot
                      </a>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          <main className="flex-1 p-6 lg:p-8 overflow-auto gradient-mesh">
            <Outlet />
          </main>
        </div>
      </div>
    </SidebarProvider>
  );
}
