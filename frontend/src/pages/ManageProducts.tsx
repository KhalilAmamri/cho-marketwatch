import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/PageHeader";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Puzzle, Plus, Pencil, Trash2, Search, Package } from "lucide-react";
import { toast } from "sonner";
import {
  ProductFormatPayload,
  ProductFormatRecord,
  createBrandAdmin,
  createCategoryAdmin,
  createProductFormatAdmin,
  createRangeAdmin,
  deleteProductFormatAdmin,
  getAdminLookups,
  getProductFormatsAdmin,
  updateProductFormatAdmin,
} from "@/lib/api";

export default function ManageProducts() {
  const queryClient = useQueryClient();

  const { data: lookups } = useQuery({
    queryKey: ["admin-lookups"],
    queryFn: getAdminLookups,
  });
  const { data: productFormats = [], isLoading } = useQuery({
    queryKey: ["admin-product-formats"],
    queryFn: getProductFormatsAdmin,
  });

  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<ProductFormatRecord | null>(null);

  const [brandId, setBrandId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [rangeId, setRangeId] = useState("");
  const [format, setFormat] = useState("");
  const [packaging, setPackaging] = useState("");

  const [newBrandName, setNewBrandName] = useState("");
  const [newCategoryName, setNewCategoryName] = useState("");
  const [newRangeName, setNewRangeName] = useState("");

  const formatOptions = lookups?.formats || [];
  const packagingOptions = lookups?.packagings || [];

  const createBrandMutation = useMutation({
    mutationFn: createBrandAdmin,
    onSuccess: (created) => {
      toast.success(`Brand "${created.name}" added`);
      setNewBrandName("");
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to add brand");
    },
  });

  const createCategoryMutation = useMutation({
    mutationFn: createCategoryAdmin,
    onSuccess: (created) => {
      toast.success(`Category "${created.name}" added`);
      setNewCategoryName("");
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to add category");
    },
  });

  const createRangeMutation = useMutation({
    mutationFn: createRangeAdmin,
    onSuccess: (created) => {
      toast.success(`Range "${created.name}" added`);
      setNewRangeName("");
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to add range");
    },
  });

  const createMutation = useMutation({
    mutationFn: createProductFormatAdmin,
    onSuccess: () => {
      toast.success("Product format created");
      queryClient.invalidateQueries({ queryKey: ["admin-product-formats"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to create product format");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ProductFormatPayload }) => updateProductFormatAdmin(id, payload),
    onSuccess: () => {
      toast.success("Product format updated");
      queryClient.invalidateQueries({ queryKey: ["admin-product-formats"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to update product format");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProductFormatAdmin,
    onSuccess: () => {
      toast.success("Product format removed");
      queryClient.invalidateQueries({ queryKey: ["admin-product-formats"] });
      queryClient.invalidateQueries({ queryKey: ["admin-lookups"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to remove product format");
    },
  });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return productFormats;
    return productFormats.filter((row) =>
      [row.brandName, row.categoryName, row.rangeName, row.format, row.packaging]
        .some((v) => v.toLowerCase().includes(q))
    );
  }, [search, productFormats]);

  function resetForm() {
    setEditingRow(null);
    setBrandId("");
    setCategoryId("");
    setRangeId("");
    setFormat("");
    setPackaging("");
  }

  function openCreate() {
    setEditingRow(null);
    setBrandId(lookups?.brands[0] ? String(lookups.brands[0].id) : "");
    setCategoryId(lookups?.categories[0] ? String(lookups.categories[0].id) : "");
    setRangeId(lookups?.ranges[0] ? String(lookups.ranges[0].id) : "");
    setFormat(formatOptions[0] || "");
    setPackaging(packagingOptions[0] || "");
    setDialogOpen(true);
  }

  function openEdit(row: ProductFormatRecord) {
    setEditingRow(row);
    setBrandId(String(row.brandId));
    setCategoryId(String(row.categoryId));
    setRangeId(String(row.rangeId));
    setFormat(row.format);
    setPackaging(row.packaging);
    setDialogOpen(true);
  }

  function handleSave() {
    if (!brandId || !categoryId || !rangeId || !format.trim() || !packaging.trim()) {
      toast.error("Please fill all fields");
      return;
    }

    const payload: ProductFormatPayload = {
      brandId: Number(brandId),
      categoryId: Number(categoryId),
      rangeId: Number(rangeId),
      format: format.trim(),
      packaging: packaging.trim(),
    };

    if (editingRow) {
      updateMutation.mutate({ id: editingRow.id, payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  function handleCreateMasterData(kind: "brand" | "category" | "range") {
    if (kind === "brand") {
      const value = newBrandName.trim();
      if (!value) {
        toast.error("Brand name is required");
        return;
      }
      createBrandMutation.mutate(value);
      return;
    }

    if (kind === "category") {
      const value = newCategoryName.trim();
      if (!value) {
        toast.error("Category name is required");
        return;
      }
      createCategoryMutation.mutate(value);
      return;
    }

    const value = newRangeName.trim();
    if (!value) {
      toast.error("Range name is required");
      return;
    }
    createRangeMutation.mutate(value);
  }

  return (
    <div>
      <PageHeader
        icon={Puzzle}
        title="Product Management"
        subtitle="Create master data (brand/category/range) and then manage product formats linked to them."
        action={
          <Button onClick={openCreate} className="rounded-xl gradient-gold text-primary-foreground font-bold shadow-lg shadow-primary/20">
            <Plus className="w-4 h-4 mr-2" /> Add Product Format
          </Button>
        }
      />

      <div className="glass-card rounded-2xl p-4 mb-4">
        <div className="mb-3">
          <h3 className="text-sm uppercase tracking-wider font-bold text-muted-foreground">Catalog Master Data</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Add Brand, Category, and Range here first. These values will appear in the Product Format form.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <InlineCreateInput
            label="Brand"
            value={newBrandName}
            onChange={setNewBrandName}
            onAdd={() => handleCreateMasterData("brand")}
            isSaving={createBrandMutation.isPending}
            placeholder="New brand"
          />
          <InlineCreateInput
            label="Category"
            value={newCategoryName}
            onChange={setNewCategoryName}
            onAdd={() => handleCreateMasterData("category")}
            isSaving={createCategoryMutation.isPending}
            placeholder="New category"
          />
          <InlineCreateInput
            label="Range"
            value={newRangeName}
            onChange={setNewRangeName}
            onAdd={() => handleCreateMasterData("range")}
            isSaving={createRangeMutation.isPending}
            placeholder="New range"
          />
        </div>
      </div>

      <div className="glass-card rounded-2xl p-4 mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search product formats..."
            className="pl-10 h-10 rounded-xl bg-background/60 border-border/50"
          />
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider">Brand</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Category</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Range</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Format</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Packaging</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-10">Loading product formats...</TableCell>
              </TableRow>
            ) : (
              filtered.map((row) => (
                <TableRow key={row.id} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                  <TableCell className="font-semibold">{row.brandName}</TableCell>
                  <TableCell>
                    <Badge className="bg-primary/10 text-primary border-primary/20 hover:bg-primary/15">{row.categoryName}</Badge>
                  </TableCell>
                  <TableCell>{row.rangeName}</TableCell>
                  <TableCell>
                    <span className="inline-flex items-center gap-1.5 text-sm">
                      <Package className="w-3.5 h-3.5 text-muted-foreground" /> {row.format}
                    </span>
                  </TableCell>
                  <TableCell>{row.packaging}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-primary/10 hover:text-primary"
                        onClick={() => openEdit(row)}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => deleteMutation.mutate(row.id)}
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
        {!isLoading && filtered.length === 0 && (
          <div className="p-12 text-center text-muted-foreground">
            <Package className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="font-medium">No product formats found</p>
          </div>
        )}
      </motion.div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">
              {editingRow ? "Edit Product Format" : "New Product Format"}
            </DialogTitle>
            <DialogDescription>
              {editingRow
                ? "Update brand, category, range, format, and packaging."
                : "Create a product format linked to brand, category, and range."}
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-2 gap-4 py-4">
            <LookupSelect
              label="Brand"
              value={brandId}
              onChange={setBrandId}
              options={(lookups?.brands || []).map((b) => ({ value: String(b.id), label: b.name }))}
            />
            <LookupSelect
              label="Category"
              value={categoryId}
              onChange={setCategoryId}
              options={(lookups?.categories || []).map((c) => ({ value: String(c.id), label: c.name }))}
            />
            <LookupSelect
              label="Range"
              value={rangeId}
              onChange={setRangeId}
              options={(lookups?.ranges || []).map((r) => ({ value: String(r.id), label: r.name }))}
            />
            <LookupSelect
              label="Format"
              value={format}
              onChange={setFormat}
              options={formatOptions.map((item) => ({ value: item, label: item }))}
            />
            <div className="col-span-2">
              <LookupSelect
                label="Packaging"
                value={packaging}
                onChange={setPackaging}
                options={packagingOptions.map((item) => ({ value: item, label: item }))}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} className="rounded-xl">Cancel</Button>
            <Button onClick={handleSave} disabled={isSaving} className="rounded-xl gradient-gold text-primary-foreground font-bold shadow-lg shadow-primary/20">
              {isSaving ? "Saving..." : editingRow ? "Save Changes" : "Create Product Format"}
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
  const hasOptions = options.length > 0;

  return (
    <div>
      <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">{label}</label>
      <Select value={value} onValueChange={onChange} disabled={!hasOptions}>
        <SelectTrigger className="h-10 rounded-xl">
          <SelectValue placeholder={`Select ${label.toLowerCase()}`} />
        </SelectTrigger>
        <SelectContent>
          {hasOptions ? (
            options.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))
          ) : (
            <SelectItem value="__no_options" disabled>
              No options available in database
            </SelectItem>
          )}
        </SelectContent>
      </Select>
    </div>
  );
}

function InlineCreateInput({
  label,
  value,
  onChange,
  onAdd,
  isSaving,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onAdd: () => void;
  isSaving: boolean;
  placeholder: string;
}) {
  return (
    <div>
      <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">{label}</label>
      <div className="flex items-center gap-2">
        <Input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          className="h-10 rounded-xl bg-background/60 border-border/50"
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onAdd();
            }
          }}
        />
        <Button onClick={onAdd} disabled={isSaving} className="h-10 rounded-xl">
          {isSaving ? "..." : "Add"}
        </Button>
      </div>
    </div>
  );
}
