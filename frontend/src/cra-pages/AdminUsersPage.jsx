import { useCallback, useEffect, useState } from "react";
import PasswordInput from "@/components/PasswordInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { adminApi } from "@/lib/api";
import { toast } from "sonner";
import { usePageTitle } from "@/lib/usePageTitle";

const PAGE = 50;
const SELECT_CLASS = "field w-auto pr-8";

/** Admin: find people, create teacher/admin accounts, hand out one-time password reset links. */
export default function AdminUsersPage() {
    usePageTitle("Users");
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [hasMore, setHasMore] = useState(false);
    const [q, setQ] = useState("");
    const [debouncedQ, setDebouncedQ] = useState("");
    const [role, setRole] = useState("");
    const [createOpen, setCreateOpen] = useState(false);
    const [form, setForm] = useState({ name: "", email: "", password: "", role: "teacher" });
    const [creating, setCreating] = useState(false);
    const [link, setLink] = useState(null); // { user, url, minutes }

    useEffect(() => {
        const t = setTimeout(() => setDebouncedQ(q), 300);
        return () => clearTimeout(t);
    }, [q]);

    const fetchPage = useCallback(
        async (offset) => {
            const rows = await adminApi.listUsers({ q: debouncedQ || undefined, role: role || undefined, limit: PAGE, offset });
            setHasMore(rows.length === PAGE);
            return rows;
        },
        [debouncedQ, role]
    );

    useEffect(() => {
        setLoading(true);
        fetchPage(0)
            .then(setUsers)
            .catch(() => toast.error("Could not load users"))
            .finally(() => setLoading(false));
    }, [fetchPage]);

    const loadMore = async () => {
        try {
            const rows = await fetchPage(users.length);
            setUsers((prev) => [...prev, ...rows]);
        } catch {
            toast.error("Could not load more users");
        }
    };

    const create = async (e) => {
        e.preventDefault();
        setCreating(true);
        try {
            const made = await adminApi.createUser(form);
            toast.success(`${made.role === "admin" ? "Admin" : made.role === "teacher" ? "Teacher" : "Student"} account created`);
            setCreateOpen(false);
            setForm({ name: "", email: "", password: "", role: "teacher" });
            setUsers(await fetchPage(0));
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Could not create the account");
        } finally {
            setCreating(false);
        }
    };

    const makeLink = async (u) => {
        try {
            const r = await adminApi.userResetLink(u.id);
            setLink({ user: u, url: `${window.location.origin}${r.reset_path}`, minutes: r.expires_in_minutes });
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Could not create a reset link");
        }
    };

    const copy = async () => {
        try {
            await navigator.clipboard.writeText(link.url);
            toast.success("Link copied");
        } catch {
            toast.error("Copy failed — select the link and copy it manually");
        }
    };

    return (
        <>
            <div className="space-y-6">
                <header className="head !mb-4">
                    <div>
                        <div className="text-overline mb-2 text-primary">Administration</div>
                        <h1 className="text-display">Users</h1>
                        <p className="lede mt-3">Create teacher and admin accounts and hand out one-time password reset links.</p>
                    </div>
                    <Button variant="pen" onClick={() => setCreateOpen(true)} data-testid="create-user-btn">
                        New account
                    </Button>
                </header>

                <div className="flex flex-wrap gap-3">
                    <Input
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                        placeholder="Search by name or email"
                        aria-label="Search users"
                        className="w-full sm:max-w-xs"
                        data-testid="user-search-input"
                    />
                    <select value={role} onChange={(e) => setRole(e.target.value)} aria-label="Filter by role" className={SELECT_CLASS} data-testid="user-role-filter">
                        <option value="">All roles</option>
                        <option value="teacher">Teachers</option>
                        <option value="student">Students</option>
                        <option value="admin">Admins</option>
                    </select>
                </div>

                {loading ? (
                    <div aria-busy="true" aria-label="Loading" className="grid gap-4">
                        <span className="sk" />
                        <span className="sk" />
                        <span className="sk" />
                    </div>
                ) : users.length === 0 ? (
                    <div className="empty">
                        <h2 className="text-xl">No users match</h2>
                        <p className="mt-2 text-sm text-muted-foreground">Try another name, email or role.</p>
                    </div>
                ) : (
                    <div className="overflow-hidden rounded-[var(--radius)] border border-border bg-card">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Name</TableHead>
                                    <TableHead className="hidden md:table-cell">Email</TableHead>
                                    <TableHead className="hidden sm:table-cell">Role</TableHead>
                                    <TableHead className="text-right"><span className="sr-only">Actions</span></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {users.map((u) => (
                                    <TableRow key={u.id} data-testid={`user-row-${u.id}`}>
                                        <TableCell className="min-w-0">
                                            <div className="font-bold">{u.name}</div>
                                            <div className="truncate text-sm text-muted-foreground md:hidden">
                                                {u.email}
                                                <span className="capitalize sm:hidden"> · {u.role}</span>
                                            </div>
                                        </TableCell>
                                        <TableCell className="hidden text-sm text-muted-foreground md:table-cell">{u.email}</TableCell>
                                        <TableCell className="hidden sm:table-cell"><Badge variant="secondary" className="capitalize">{u.role}</Badge></TableCell>
                                        <TableCell className="whitespace-nowrap text-right">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => makeLink(u)}
                                                aria-label={`Reset password for ${u.name}`}
                                                data-testid={`reset-link-${u.id}`}
                                            >
                                                Reset<span className="hidden sm:inline">&nbsp;password</span>
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                )}
                {hasMore && !loading && (
                    <div className="text-center">
                        <Button variant="outline" onClick={loadMore} data-testid="users-load-more">Load more</Button>
                    </div>
                )}
            </div>

            <Dialog open={createOpen} onOpenChange={setCreateOpen}>
                <DialogContent className="max-w-md" data-testid="create-user-dialog">
                    <DialogHeader><DialogTitle>New account</DialogTitle></DialogHeader>
                    <form onSubmit={create} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="nu-name">Full name</Label>
                            <Input id="nu-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="nu-email">Email</Label>
                            <Input id="nu-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="nu-role">Role</Label>
                            <select id="nu-role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className={`${SELECT_CLASS} w-full`}>
                                <option value="teacher">Teacher</option>
                                <option value="student">Student</option>
                                <option value="admin">Admin</option>
                            </select>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="nu-password">Temporary password</Label>
                            <PasswordInput id="nu-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} autoComplete="new-password" minLength={8} required />
                            <p className="text-sm text-muted-foreground">At least 8 characters. Ask them to change it from Account after signing in.</p>
                        </div>
                        <Button type="submit" className="w-full" disabled={creating} data-testid="create-user-submit">
                            {creating ? "Creating…" : "Create account"}
                        </Button>
                    </form>
                </DialogContent>
            </Dialog>

            <Dialog open={!!link} onOpenChange={(o) => !o && setLink(null)}>
                <DialogContent className="max-w-lg" data-testid="reset-link-dialog">
                    <DialogHeader><DialogTitle>Password reset link</DialogTitle></DialogHeader>
                    {link && (
                        <div className="space-y-4">
                            <p className="text-sm text-muted-foreground">
                                Give this link to <span className="font-bold text-foreground">{link.user.name}</span>. It works once and
                                expires in {link.minutes} minutes. Anyone with the link can set the password, so send it privately.
                            </p>
                            <Input readOnly value={link.url} onFocus={(e) => e.target.select()} aria-label="Reset link" data-testid="reset-link-url" />
                            <Button onClick={copy} className="w-full" data-testid="copy-reset-link">Copy link</Button>
                        </div>
                    )}
                </DialogContent>
            </Dialog>
        </>
    );
}
