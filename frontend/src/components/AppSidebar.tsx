import {
  Tag, TrendingUp, Store, Sparkles, Puzzle, Link2, Users, LogOut, ChevronRight, Activity, MapPinned, Building2,
} from "lucide-react";
import choLogo from "@/assets/cho-group-logo.png";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
  SidebarFooter, SidebarHeader, useSidebar,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const marketPages = [
  { title: "Prices Explorer", url: "/prices", icon: Tag },
  { title: "Price Trends", url: "/trends", icon: TrendingUp },
  { title: "Store Comparison", url: "/comparison", icon: Store },
  { title: "Price Forecast", url: "/forecast", icon: Sparkles },
];

const adminPages = [
  { title: "Products & Catalog", url: "/admin/products", icon: Puzzle },
  { title: "URLs", url: "/admin/urls", icon: Link2 },
  { title: "Stores Management", url: "/admin/stores", icon: Building2 },
  { title: "Retail Presence", url: "/admin/retail-presence", icon: MapPinned },
  { title: "Operational Visibility", url: "/admin/operations", icon: Activity },
  { title: "Users", url: "/admin/users", icon: Users },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";
  const location = useLocation();
  const { user, isAdmin, logout } = useAuth();

  const isActive = (path: string) => location.pathname === path;

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className={cn("pb-3", collapsed ? "p-2 pt-3" : "p-4")}>
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
              <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-primary opacity-80">
                Price Tracker
              </p>
            </div>
          )}
        </div>
      </SidebarHeader>

      {!collapsed && user && (
        <div className="mx-4 mb-3 p-3 rounded-xl bg-sidebar-accent/50 border border-sidebar-border">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg gradient-teal flex items-center justify-center text-xs font-bold text-accent-foreground">
              {user.fullName.charAt(0)}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-semibold text-sidebar-foreground truncate">{user.fullName}</p>
              <p className="text-[10px] text-sidebar-foreground/50 uppercase font-bold tracking-wider">{user.role}</p>
            </div>
          </div>
        </div>
      )}

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel className="text-[10px] uppercase tracking-[0.2em] font-bold text-sidebar-foreground/40 mb-1">
            Analytics
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {marketPages.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild isActive={isActive(item.url)}>
                    <NavLink
                      to={item.url}
                      className="group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-all duration-200"
                      activeClassName="!bg-primary/15 !text-primary font-semibold"
                    >
                      <item.icon className="h-4 w-4 flex-shrink-0" />
                      {!collapsed && <span>{item.title}</span>}
                      {!collapsed && isActive(item.url) && (
                        <ChevronRight className="ml-auto h-3.5 w-3.5 text-primary/60" />
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
            <Separator className="mx-4 w-auto bg-sidebar-border/50" />
            <SidebarGroup>
              <SidebarGroupLabel className="text-[10px] uppercase tracking-[0.2em] font-bold text-sidebar-foreground/40 mb-1">
                Admin
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {adminPages.map((item) => (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton asChild isActive={isActive(item.url)}>
                        <NavLink
                          to={item.url}
                          className="group flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-all duration-200"
                          activeClassName="!bg-primary/15 !text-primary font-semibold"
                        >
                          <item.icon className="h-4 w-4 flex-shrink-0" />
                          {!collapsed && <span>{item.title}</span>}
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

      <SidebarFooter className="p-3 pt-2">
        {!collapsed && (
          <p className="text-[10px] text-sidebar-foreground/30 mb-2 px-2 font-medium">Prices normalized to EUR</p>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-2.5 w-full px-3 py-2.5 rounded-xl text-sm font-medium text-sidebar-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-all duration-200"
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && "Sign out"}
        </button>
      </SidebarFooter>
    </Sidebar>
  );
}
