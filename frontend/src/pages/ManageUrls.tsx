import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Link2, Plus, Trash2, Search, ExternalLink, Globe, Pencil } from "lucide-react";
import { toast } from "sonner";
import {
  ProductUrlPayload,
  ProductUrlRecord,
  createProductUrlAdmin,
  deleteProductUrlAdmin,
  getAdminLookups,
  getProductUrlsAdmin,
  setProductUrlActiveAdmin,
  updateProductUrlAdmin,
} from "@/lib/api";

export default function ManageUrls() {
  const queryClient = useQueryClient();

  const { data: lookups } = useQuery({
    queryKey: ["admin-lookups"],
    queryFn: getAdminLookups,
  });
  const { data: urls = [], isLoading } = useQuery({
    queryKey: ["admin-product-urls"],
    queryFn: getProductUrlsAdmin,
  });

  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<ProductUrlRecord | null>(null);

  const [websiteId, setWebsiteId] = useState("");
  const [storeId, setStoreId] = useState("none");
  const [productFormatId, setProductFormatId] = useState("");
  const [url, setUrl] = useState("");
  const [isActive, setIsActive] = useState(true);

  const createMutation = useMutation({
    mutationFn: createProductUrlAdmin,
    onSuccess: () => {
      toast.success("URL created");
      queryClient.invalidateQueries({ queryKey: ["admin-product-urls"] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to create URL");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProductUrlPayload }) => updateProductUrlAdmin(id, payload),
    onSuccess: () => {
      toast.success("URL updated");
      queryClient.invalidateQueries({ queryKey: ["admin-product-urls"] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to update URL");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProductUrlAdmin,
    onSuccess: () => {
      toast.success("URL removed");
      queryClient.invalidateQueries({ queryKey: ["admin-product-urls"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to remove URL");
    },
  });

  const activeMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => setProductUrlActiveAdmin(id, active),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-product-urls"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to update URL status");
    },
  });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return urls;
    return urls.filter((row) =>
      [row.websiteName, row.country || "", row.storeCode || "", row.productLabel, row.url]
        .some((v) => v.toLowerCase().includes(q))
    );
  }, [search, urls]);

  const activeWebsites = useMemo(
    () => (lookups?.websites || []).filter((website) => website.scraperStatus === "active"),
    [lookups],
  );

  const websiteSelectOptions = useMemo(() => {
    const options = activeWebsites.map((website) => ({
      value: String(website.id),
      label: `${website.siteName}${website.country ? ` (${website.country})` : ""}`,
    }));

    if (
      editingRow
      && !activeWebsites.some((website) => website.id === editingRow.websiteId)
    ) {
      options.unshift({
        value: String(editingRow.websiteId),
        label: `${editingRow.websiteName}${editingRow.country ? ` (${editingRow.country})` : ""} - pending`,
      });
    }

    return options;
  }, [activeWebsites, editingRow]);

  const storesForWebsite = useMemo(() => {
    if (!websiteId || !lookups) return [];
    const selectedWebsite = Number(websiteId);
    return lookups.stores.filter((store) => store.websiteId === selectedWebsite);
  }, [websiteId, lookups]);

  function resetForm() {
    setEditingRow(null);
    setWebsiteId("");
    setStoreId("none");
    setProductFormatId("");
    setUrl("");
    setIsActive(true);
  }

  function openCreate() {
    if (!activeWebsites.length) {
      toast.error("No active websites available. Activate a website before adding URLs.");
      return;
    }

    setEditingRow(null);
    setWebsiteId(String(activeWebsites[0].id));
    setStoreId("none");
    setProductFormatId(lookups?.productFormats[0] ? String(lookups.productFormats[0].id) : "");
    setUrl("");
    setIsActive(true);
    setDialogOpen(true);
  }

  function openEdit(row: ProductUrlRecord) {
    setEditingRow(row);
    setWebsiteId(String(row.websiteId));
    setStoreId(row.storeId ? String(row.storeId) : "none");
    setProductFormatId(String(row.productFormatId));
    setUrl(row.url);
    setIsActive(row.isActive);
    setDialogOpen(true);
  }

  function handleSave() {
    if (!websiteId || !productFormatId || !url.trim()) {
      toast.error("Please complete required fields");
      return;
    }

    const selectedWebsite = (lookups?.websites || []).find((website) => String(website.id) === websiteId) || null;
    if (!selectedWebsite || selectedWebsite.scraperStatus !== "active") {
      toast.error("Only active websites can be linked to scraping URLs");
      return;
    }

    const payload: ProductUrlPayload = {
      websiteId: Number(websiteId),
      storeId: storeId === "none" ? null : Number(storeId),
      productFormatId: Number(productFormatId),
      url: url.trim(),
      isActive,
    };

    if (editingRow) {
      updateMutation.mutate({ id: editingRow.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <PageHeader
        icon={Link2}
        title="Scraping URLs"
        subtitle="Manage product URLs backed by website, store, and product-format relations."
        action={
          <Button
            onClick={openCreate}
            disabled={!activeWebsites.length}
            className="rounded-xl gradient-gold text-primary-foreground font-bold shadow-lg shadow-primary/20"
          >
            <Plus className="w-4 h-4 mr-2" /> Add URL
          </Button>
        }
      />

      <div className="glass-card rounded-2xl p-4 mb-6">
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search URLs..."
              className="pl-10 h-10 rounded-xl bg-background/60 border-border/50"
            />
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-accent" /> {urls.filter((row) => row.isActive).length} active
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-muted-foreground" /> {urls.filter((row) => !row.isActive).length} inactive
            </span>
          </div>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider">Website</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Country</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Store</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Product</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Status</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-10">Loading URLs...</TableCell>
              </TableRow>
            ) : (
              filtered.map((row) => (
                <TableRow key={row.id} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-muted-foreground" />
                      <span className="font-semibold">{row.websiteName}</span>
                    </div>
                  </TableCell>
                  <TableCell>{row.country || "-"}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="rounded-lg">{row.storeCode || "No Store"}</Badge>
                  </TableCell>
                  <TableCell className="text-sm max-w-[260px] truncate">{row.productLabel}</TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={row.isActive}
                      onCheckedChange={(checked) => activeMutation.mutate({ id: row.id, active: checked })}
                      disabled={activeMutation.isPending}
                    />
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-primary/10 hover:text-primary" onClick={() => openEdit(row)}>
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-accent/10 hover:text-accent" asChild>
                        <a href={row.url} target="_blank" rel="noopener noreferrer"><ExternalLink className="w-3.5 h-3.5" /></a>
                      </Button>
                      <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-destructive/10 hover:text-destructive" onClick={() => deleteMutation.mutate(row.id)} disabled={deleteMutation.isPending}>
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        {!isLoading && filtered.length === 0 && (
          <div className="p-12 text-center text-muted-foreground">
            <Link2 className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="font-medium">No URLs found</p>
          </div>
        )}
      </motion.div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">{editingRow ? "Edit URL" : "Add Scraping URL"}</DialogTitle>
            <DialogDescription>
              {editingRow ? "Update URL mapping and activation status." : "Link a website/store to a product format for scraping."}
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-4">
            <div className="col-span-2">
              <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Product URL</label>
              <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://..." className="h-10 rounded-xl" />
            </div>

            <LookupSelect
              label="Website"
              value={websiteId}
              onChange={(value) => {
                setWebsiteId(value);
                setStoreId("none");
              }}
              options={websiteSelectOptions}
            />

            <LookupSelect
              label="Store"
              value={storeId}
              onChange={setStoreId}
              options={[{ value: "none", label: "No Store" }, ...storesForWebsite.map((s) => ({ value: String(s.id), label: s.label }))]}
            />

            <div className="col-span-2">
              <LookupSelect
                label="Product Format"
                value={productFormatId}
                onChange={setProductFormatId}
                options={(lookups?.productFormats || []).map((pf) => ({ value: String(pf.id), label: pf.label }))}
              />
            </div>

            <div className="col-span-2 flex items-center justify-between rounded-xl border border-border/50 bg-background/60 p-3">
              <div>
                <p className="text-sm font-semibold">Active URL</p>
                <p className="text-xs text-muted-foreground">Only active URLs are processed by scrapers.</p>
                <p className="text-xs text-muted-foreground">Only websites with scraper_status = active can be selected here.</p>
              </div>
              <Switch checked={isActive} onCheckedChange={setIsActive} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} className="rounded-xl">Cancel</Button>
            <Button onClick={handleSave} disabled={isSaving} className="rounded-xl gradient-gold text-primary-foreground font-bold shadow-lg shadow-primary/20">
              {isSaving ? "Saving..." : editingRow ? "Save Changes" : "Add URL"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function LookupSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <div>
      <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">{label}</label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="h-10 rounded-xl">
          <SelectValue placeholder={`Select ${label.toLowerCase()}`} />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
