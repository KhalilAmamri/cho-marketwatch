import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  ScraperStatus,
  createWebsiteAdmin,
  createStoreAdmin,
  deleteWebsiteAdmin,
  deleteStoreAdmin,
  getStoresAdmin,
  getWebsitesAdmin,
  updateWebsiteAdmin,
  updateStoreAdmin,
} from "@/lib/api";
import { Building2, Database, Globe2, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

function normalizeBaseUrl(value: string | null): string | null {
  if (!value) return null;

  try {
    const parsed = new URL(value);
    return `${parsed.protocol}//${parsed.host}`;
  } catch {
    return null;
  }
}

function getStatusBadgeClass(status: ScraperStatus): string {
  if (status === "pending") {
    return "bg-primary/10 text-primary border-primary/20 hover:bg-primary/10";
  }

  return "bg-accent/10 text-accent border-accent/20 hover:bg-accent/10";
}

export default function StoresManagement() {
  const queryClient = useQueryClient();

  const { data: websites = [], isLoading: isWebsitesLoading } = useQuery({
    queryKey: ["admin-websites"],
    queryFn: getWebsitesAdmin,
  });

  const { data: stores = [], isLoading: isStoresLoading } = useQuery({
    queryKey: ["admin-stores"],
    queryFn: getStoresAdmin,
  });

  const [selectedWebsiteId, setSelectedWebsiteId] = useState("");
  const [storeCode, setStoreCode] = useState("");
  const [storeName, setStoreName] = useState("");
  const [editingStoreId, setEditingStoreId] = useState<number | null>(null);

  const [websiteName, setWebsiteName] = useState("");
  const [websiteBaseUrl, setWebsiteBaseUrl] = useState("");
  const [websiteCountry, setWebsiteCountry] = useState("");
  const [editingWebsiteId, setEditingWebsiteId] = useState<number | null>(null);

  useEffect(() => {
    if (!websites.length) {
      if (selectedWebsiteId) setSelectedWebsiteId("");
      return;
    }

    const hasSelectedWebsite = websites.some((website) => String(website.id) === selectedWebsiteId);
    if (!hasSelectedWebsite) {
      setSelectedWebsiteId(String(websites[0].id));
    }
  }, [selectedWebsiteId, websites]);

  const selectedWebsite = useMemo(
    () => websites.find((website) => String(website.id) === selectedWebsiteId) || null,
    [selectedWebsiteId, websites],
  );

  const storesForWebsite = useMemo(
    () => stores.filter((store) => String(store.websiteId) === selectedWebsiteId),
    [stores, selectedWebsiteId],
  );

  const pendingWebsiteCount = useMemo(
    () => websites.filter((website) => website.scraperStatus === "pending").length,
    [websites],
  );

  const createMutation = useMutation({
    mutationFn: createStoreAdmin,
    onSuccess: () => {
      toast.success("Store created");
      queryClient.invalidateQueries({ queryKey: ["admin-stores"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
      setStoreCode("");
      setStoreName("");
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to create store");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { websiteId: number; storeCode: string; storeName: string | null } }) =>
      updateStoreAdmin(id, payload),
    onSuccess: () => {
      toast.success("Store updated");
      queryClient.invalidateQueries({ queryKey: ["admin-stores"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
      resetStoreForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to update store");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteStoreAdmin,
    onSuccess: () => {
      toast.success("Store removed");
      queryClient.invalidateQueries({ queryKey: ["admin-stores"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to remove store");
    },
  });

  const createWebsiteMutation = useMutation({
    mutationFn: createWebsiteAdmin,
    onSuccess: () => {
      toast.success("Website created with scraper_status = pending");
      queryClient.invalidateQueries({ queryKey: ["admin-websites"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
      resetWebsiteForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to create website");
    },
  });

  const updateWebsiteMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { siteName: string; baseUrl: string | null; country: string | null } }) =>
      updateWebsiteAdmin(id, payload),
    onSuccess: () => {
      toast.success("Website updated");
      queryClient.invalidateQueries({ queryKey: ["admin-websites"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
      resetWebsiteForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to update website");
    },
  });

  const deleteWebsiteMutation = useMutation({
    mutationFn: deleteWebsiteAdmin,
    onSuccess: (_, websiteId) => {
      toast.success("Website removed");
      queryClient.invalidateQueries({ queryKey: ["admin-websites"] });
      queryClient.invalidateQueries({ queryKey: ["admin-stores"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
      if (editingWebsiteId === websiteId) {
        resetWebsiteForm();
      }
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to remove website");
    },
  });

  const isStoreSaving = createMutation.isPending || updateMutation.isPending;
  const isWebsiteSaving = createWebsiteMutation.isPending || updateWebsiteMutation.isPending;

  function resetStoreForm() {
    setEditingStoreId(null);
    setStoreCode("");
    setStoreName("");
  }

  function handleStoreSubmit() {
    if (!selectedWebsiteId) {
      toast.error("Please select a website first");
      return;
    }

    const code = storeCode.trim();
    if (!code) {
      toast.error("Store code is required");
      return;
    }

    const payload = {
      websiteId: Number(selectedWebsiteId),
      storeCode: code,
      storeName: storeName.trim() || null,
    };

    if (editingStoreId) {
      updateMutation.mutate({ id: editingStoreId, payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  function startEditStore(store: { id: number; websiteId: number; storeCode: string; storeName: string | null }) {
    setEditingStoreId(store.id);
    setSelectedWebsiteId(String(store.websiteId));
    setStoreCode(store.storeCode);
    setStoreName(store.storeName || "");
  }

  function resetWebsiteForm() {
    setEditingWebsiteId(null);
    setWebsiteName("");
    setWebsiteBaseUrl("");
    setWebsiteCountry("");
  }

  function handleWebsiteSubmit() {
    const normalizedName = websiteName.trim();
    if (!normalizedName) {
      toast.error("Website name is required");
      return;
    }

    const rawBaseUrl = websiteBaseUrl.trim();
    if (!rawBaseUrl) {
      toast.error("Base URL is required");
      return;
    }

    const normalizedBaseUrl = normalizeBaseUrl(rawBaseUrl);
    if (!normalizedBaseUrl) {
      toast.error("Base URL must be a valid URL");
      return;
    }

    const normalizedCountry = websiteCountry.trim();
    if (!normalizedCountry) {
      toast.error("Country is required");
      return;
    }

    const lowerName = normalizedName.toLowerCase();
    const alreadyExists = websites.some(
      (website) => website.siteName.trim().toLowerCase() === lowerName && website.id !== editingWebsiteId,
    );
    if (alreadyExists) {
      toast.error("This website already exists");
      return;
    }

    const payload = {
      siteName: normalizedName,
      baseUrl: normalizedBaseUrl,
      country: normalizedCountry,
    };

    if (editingWebsiteId) {
      updateWebsiteMutation.mutate({ id: editingWebsiteId, payload });
    } else {
      createWebsiteMutation.mutate(payload);
    }
  }

  function startEditWebsite(website: { id: number; siteName: string; baseUrl: string; country: string }) {
    setEditingWebsiteId(website.id);
    setWebsiteName(website.siteName);
    setWebsiteBaseUrl(website.baseUrl);
    setWebsiteCountry(website.country);
  }

  function removeWebsite(websiteId: number) {
    deleteWebsiteMutation.mutate(websiteId);
  }

  const websiteLabel = selectedWebsite
    ? `${selectedWebsite.siteName}${selectedWebsite.country ? ` (${selectedWebsite.country})` : ""}`
    : "No website selected";

  return (
    <div>
      <PageHeader
        icon={Building2}
        title="Stores Management"
        subtitle="Manage backend websites and stores. Website scraper_status is managed by the database."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <MetricCard label="Websites" value={websites.length} icon={Globe2} accentColor="gold" />
        <MetricCard label="Pending Websites" value={pendingWebsiteCount} icon={Globe2} />
        <MetricCard label="Total Stores" value={stores.length} icon={Database} accentColor="teal" />
        <MetricCard label="Stores In Selected Website" value={storesForWebsite.length} icon={Building2} />
      </div>

      <div className="glass-card rounded-2xl p-5 mb-6">
        <p className="text-[10px] uppercase tracking-[0.15em] font-bold text-muted-foreground mb-3">
          {editingWebsiteId ? "Edit Website" : "Add Website"}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="lg:col-span-2">
            <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Site Name</label>
            <Input
              value={websiteName}
              onChange={(event) => setWebsiteName(event.target.value)}
              placeholder="e.g. ICA Sweden"
              className="h-10 rounded-xl"
            />
          </div>

          <div className="lg:col-span-2">
            <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Base URL</label>
            <Input
              value={websiteBaseUrl}
              onChange={(event) => setWebsiteBaseUrl(event.target.value)}
              placeholder="https://example.com"
              required
              className="h-10 rounded-xl"
            />
          </div>

          <div>
            <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Country</label>
            <Input
              value={websiteCountry}
              onChange={(event) => setWebsiteCountry(event.target.value)}
              placeholder="e.g. Sweden"
              required
              className="h-10 rounded-xl"
            />
          </div>

          <div className="md:col-span-2 lg:col-span-4 flex items-end gap-2">
            <Button
              type="button"
              onClick={handleWebsiteSubmit}
              disabled={isWebsiteSaving}
              className="rounded-xl gradient-gold text-primary-foreground font-bold shadow-lg shadow-primary/20"
            >
              <Plus className="w-4 h-4 mr-2" />
              {isWebsiteSaving ? "Saving..." : editingWebsiteId ? "Save Website" : "Add Website"}
            </Button>

            <Button type="button" variant="outline" onClick={resetWebsiteForm} className="rounded-xl">
              {editingWebsiteId ? "Cancel Edit" : "Reset Inputs"}
            </Button>
          </div>
        </div>

        <p className="text-xs text-muted-foreground mt-3">
          Site name, base URL, and country are all required. New websites are created with scraper_status = pending by backend logic.
        </p>
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden mb-6">
        <div className="p-4 border-b border-border/50 flex items-center justify-between">
          <h3 className="text-sm uppercase tracking-wider font-bold text-muted-foreground">Websites</h3>
          <p className="text-xs text-muted-foreground">Managed in backend</p>
        </div>

        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider">Site Name</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Base URL</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Country</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">scraper_status</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Created At</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {isWebsitesLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-10">Loading websites...</TableCell>
              </TableRow>
            ) : websites.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-10">No websites found.</TableCell>
              </TableRow>
            ) : (
              websites.map((website) => (
                <TableRow key={website.id} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                  <TableCell className="font-semibold">{website.siteName}</TableCell>
                  <TableCell>
                    {website.baseUrl ? (
                      <a href={website.baseUrl} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline underline-offset-2">
                        {website.baseUrl}
                      </a>
                    ) : (
                      "-"
                    )}
                  </TableCell>
                  <TableCell>{website.country || "-"}</TableCell>
                  <TableCell>
                    <Badge className={getStatusBadgeClass(website.scraperStatus)}>{website.scraperStatus}</Badge>
                  </TableCell>
                  <TableCell>{website.createdAt ? new Date(website.createdAt).toLocaleString() : "-"}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-primary/10 hover:text-primary"
                        onClick={() => startEditWebsite(website)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => removeWebsite(website.id)}
                        disabled={deleteWebsiteMutation.isPending}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </motion.div>

      <div className="glass-card rounded-2xl p-5 mb-6">
        <p className="text-[10px] uppercase tracking-[0.15em] font-bold text-muted-foreground mb-3">
          {editingStoreId ? "Edit Store" : "Add Store"}
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="lg:col-span-2">
            <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Website (backend)</label>
            <Select value={selectedWebsiteId} onValueChange={setSelectedWebsiteId}>
              <SelectTrigger className="h-10 rounded-xl">
                <SelectValue placeholder="Select website" />
              </SelectTrigger>
              <SelectContent>
                {websites.map((website) => (
                  <SelectItem key={website.id} value={String(website.id)}>
                    {website.siteName}{website.country ? ` (${website.country})` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Store Code</label>
            <Input
              value={storeCode}
              onChange={(event) => setStoreCode(event.target.value)}
              placeholder="e.g. helsinki-001"
              className="h-10 rounded-xl"
            />
          </div>

          <div>
            <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Store Name</label>
            <Input
              value={storeName}
              onChange={(event) => setStoreName(event.target.value)}
              placeholder="Optional"
              className="h-10 rounded-xl"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 mt-4">
          <Button
            onClick={handleStoreSubmit}
            className="rounded-xl gradient-gold text-primary-foreground font-bold shadow-lg shadow-primary/20"
            disabled={!websites.length || isStoreSaving}
          >
            <Plus className="w-4 h-4 mr-2" />
            {isStoreSaving ? "Saving..." : editingStoreId ? "Save Changes" : "Add Store"}
          </Button>

          <Button
            type="button"
            variant="outline"
            onClick={resetStoreForm}
            className="rounded-xl"
          >
            {editingStoreId ? "Cancel Edit" : "Reset Inputs"}
          </Button>
        </div>

        <p className="text-xs text-muted-foreground mt-3">
          Store CRUD is linked to backend websites directly.
        </p>
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-border/50 flex items-center justify-between">
          <h3 className="text-sm uppercase tracking-wider font-bold text-muted-foreground">Website Stores</h3>
          <p className="text-xs text-muted-foreground">{websiteLabel}</p>
        </div>

        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider">Website</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Country</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Store Code</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Store Name</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Created At</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {isWebsitesLoading || isStoresLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-10">Loading websites and stores...</TableCell>
              </TableRow>
            ) : !selectedWebsiteId ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-10">No website selected.</TableCell>
              </TableRow>
            ) : storesForWebsite.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-10">No stores found for this website yet.</TableCell>
              </TableRow>
            ) : (
              storesForWebsite.map((store) => (
                <TableRow key={store.id} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                  <TableCell>
                    <Badge variant="outline" className="rounded-lg border-accent/30 text-accent">{store.websiteName}</Badge>
                  </TableCell>
                  <TableCell>{store.country || "-"}</TableCell>
                  <TableCell className="font-semibold">{store.storeCode}</TableCell>
                  <TableCell>{store.storeName || "-"}</TableCell>
                  <TableCell>{store.createdAt ? new Date(store.createdAt).toLocaleString() : "-"}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-primary/10 hover:text-primary"
                        onClick={() => startEditStore(store)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => deleteMutation.mutate(store.id)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </motion.div>
    </div>
  );
}
