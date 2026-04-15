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
import { Users, Plus, Pencil, Trash2, Search, ShieldCheck, User } from "lucide-react";
import { toast } from "sonner";
import {
  AdminUserCreatePayload,
  AdminUserRecord,
  createUserAdmin,
  deleteUserAdmin,
  getUsersAdmin,
  setUserActiveAdmin,
  updateUserAdmin,
} from "@/lib/api";

export default function ManageUsers() {
  const queryClient = useQueryClient();

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: getUsersAdmin,
  });

  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<AdminUserRecord | null>(null);

  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "user">("user");

  const createMutation = useMutation({
    mutationFn: createUserAdmin,
    onSuccess: () => {
      toast.success("User created");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to create user");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, fullNameValue, roleValue }: { id: number; fullNameValue: string; roleValue: "admin" | "user" }) =>
      updateUserAdmin(id, {
        fullName: fullNameValue.trim() || null,
        role: roleValue,
      }),
    onSuccess: () => {
      toast.success("User updated");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
      setDialogOpen(false);
      resetForm();
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to update user");
    },
  });

  const activeMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) => setUserActiveAdmin(id, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to update status");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteUserAdmin,
    onSuccess: () => {
      toast.success("User removed");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || "Failed to remove user");
    },
  });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter((row) =>
      [row.username, row.fullName || "", row.role]
        .some((v) => v.toLowerCase().includes(q))
    );
  }, [search, users]);

  function resetForm() {
    setEditingUser(null);
    setUsername("");
    setFullName("");
    setPassword("");
    setRole("user");
  }

  function openCreate() {
    resetForm();
    setDialogOpen(true);
  }

  function openEdit(user: AdminUserRecord) {
    setEditingUser(user);
    setUsername(user.username);
    setFullName(user.fullName || "");
    setPassword("");
    setRole(user.role);
    setDialogOpen(true);
  }

  function handleSave() {
    if (!username.trim()) {
      toast.error("Username is required");
      return;
    }

    if (editingUser) {
      updateMutation.mutate({ id: editingUser.id, fullNameValue: fullName, roleValue: role });
      return;
    }

    if (!password.trim()) {
      toast.error("Password is required");
      return;
    }

    const payload: AdminUserCreatePayload = {
      username: username.trim(),
      password: password.trim(),
      fullName: fullName.trim() || null,
      role,
      isActive: true,
    };
    createMutation.mutate(payload);
  }

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <div>
      <PageHeader
        icon={Users}
        title="User Management"
        subtitle="Create, update, activate, and remove user accounts from database-backed admin APIs."
        action={
          <Button onClick={openCreate} className="rounded-xl gradient-gold text-primary-foreground font-bold shadow-lg shadow-primary/20">
            <Plus className="w-4 h-4 mr-2" /> Add User
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
              placeholder="Search users..."
              className="pl-10 h-10 rounded-xl bg-background/60 border-border/50"
            />
          </div>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-primary" /> {users.filter((row) => row.role === "admin").length} admins
            </span>
            <span className="inline-flex items-center gap-1.5">
              <User className="w-3.5 h-3.5" /> {users.filter((row) => row.role === "user").length} users
            </span>
          </div>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-2xl overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="font-bold text-xs uppercase tracking-wider">User</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Role</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-center">Active</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider">Last Login</TableHead>
              <TableHead className="font-bold text-xs uppercase tracking-wider text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-10">Loading users...</TableCell>
              </TableRow>
            ) : (
              filtered.map((row) => (
                <TableRow key={row.id} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs">
                        {(row.fullName || row.username)
                          .split(" ")
                          .map((part) => part.charAt(0))
                          .join("")
                          .slice(0, 2)
                          .toUpperCase()}
                      </div>
                      <div>
                        <p className="font-semibold text-sm">{row.fullName || row.username}</p>
                        <p className="text-xs text-muted-foreground">@{row.username}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge className={row.role === "admin" ? "bg-primary/10 text-primary border-primary/20 hover:bg-primary/15" : "bg-muted text-muted-foreground"}>
                      {row.role === "admin" && <ShieldCheck className="w-3 h-3 mr-1" />}
                      {row.role}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Switch
                      checked={row.isActive}
                      onCheckedChange={(checked) => activeMutation.mutate({ id: row.id, isActive: checked })}
                      disabled={activeMutation.isPending}
                    />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{row.lastLogin || "Never"}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-primary/10 hover:text-primary" onClick={() => openEdit(row)}>
                        <Pencil className="w-3.5 h-3.5" />
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
            <Users className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="font-medium">No users found</p>
          </div>
        )}
      </motion.div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-bold">{editingUser ? "Edit User" : "New User"}</DialogTitle>
            <DialogDescription>
              {editingUser ? "Update user profile and role." : "Create a new account with role and password."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Username</label>
                <Input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Username"
                  className="h-10 rounded-xl"
                  disabled={Boolean(editingUser)}
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Full Name</label>
                <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Full Name" className="h-10 rounded-xl" />
              </div>
            </div>
            {!editingUser && (
              <div>
                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Password</label>
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" className="h-10 rounded-xl" />
              </div>
            )}
            <div>
              <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider mb-1.5 block">Role</label>
              <Select value={role} onValueChange={(value) => setRole(value as "admin" | "user") }>
                <SelectTrigger className="h-10 rounded-xl"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)} className="rounded-xl">Cancel</Button>
            <Button onClick={handleSave} disabled={isSaving} className="rounded-xl gradient-gold text-primary-foreground font-bold shadow-lg shadow-primary/20">
              {isSaving ? "Saving..." : editingUser ? "Save Changes" : "Create User"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
