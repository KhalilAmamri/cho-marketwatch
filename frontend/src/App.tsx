import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { LoginPage } from "@/components/LoginPage";
import { DashboardLayout } from "@/components/DashboardLayout";
import PricesExplorer from "@/pages/PricesExplorer";
import PriceTrends from "@/pages/PriceTrends";
import OperationalVisibility from "@/pages/OperationalVisibility";
import RetailPresence from "@/pages/RetailPresence";
import ManageProducts from "@/pages/ManageProducts";
import ManageUrls from "@/pages/ManageUrls";
import StoresManagement from "@/pages/StoresManagement";
import ManageUsers from "@/pages/ManageUsers";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient();

function ProtectedRoutes() {
  const { isAuthenticated, isAdmin, isLoading } = useAuth();

  if (isLoading) {
    return <div className="min-h-screen grid place-items-center text-muted-foreground">Loading dashboard...</div>;
  }

  if (!isAuthenticated) return <LoginPage />;

  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/dashboard" element={<Navigate to="/trends" replace />} />
        <Route path="/prices" element={<PricesExplorer />} />
        <Route path="/trends" element={<PriceTrends />} />
        <Route path="/retail-presence" element={<RetailPresence />} />
        <Route path="/comparison" element={<Navigate to="/trends" replace />} />
        {isAdmin && (
          <>
            <Route path="/admin/operations" element={<OperationalVisibility />} />
            <Route path="/admin/retail-presence" element={<Navigate to="/retail-presence" replace />} />
            <Route path="/admin/products" element={<ManageProducts />} />
            <Route path="/admin/urls" element={<ManageUrls />} />
            <Route path="/admin/stores" element={<StoresManagement />} />
            <Route path="/admin/users" element={<ManageUsers />} />
          </>
        )}
        {!isAdmin && <Route path="/admin/*" element={<Navigate to="/dashboard" replace />} />}
        <Route path="/" element={<Navigate to="/trends" replace />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <TooltipProvider>
        <Sonner />
        <BrowserRouter>
          <ProtectedRoutes />
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
