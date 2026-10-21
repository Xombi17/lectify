import { useState } from "react";
import AppShell from "@/components/AppShell";
import PasswordInput from "@/components/PasswordInput";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";
import { authApi } from "@/lib/api";
import { toast } from "sonner";
import { usePageTitle } from "@/lib/usePageTitle";

/** Account settings for every role: edit your display name and change your password. */
export default function AccountPage() {
    usePageTitle("Account");
    const { user, updateUser, applySession } = useAuth();
    const [name, setName] = useState(user?.name || "");
    const [savingName, setSavingName] = useState(false);
    const [current, setCurrent] = useState("");
    const [next, setNext] = useState("");
    const [confirm, setConfirm] = useState("");
    const [pwError, setPwError] = useState("");
    const [savingPw, setSavingPw] = useState(false);

    const saveName = async (e) => {
        e.preventDefault();
        setSavingName(true);
        try {
            const updated = await authApi.updateProfile(name.trim());
            updateUser(updated);
            toast.success("Name updated");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Could not update your name");
        } finally {
            setSavingName(false);
        }
    };

    const savePassword = async (e) => {
        e.preventDefault();
        setPwError("");
        if (next !== confirm) {
            setPwError("The two new passwords don't match.");
            return;
        }
        setSavingPw(true);
        try {
            const { access_token, user: u } = await authApi.changePassword(current, next);
            applySession(access_token, u);
            setCurrent("");
            setNext("");
            setConfirm("");
            toast.success("Password changed");
        } catch (err) {
            const detail = err?.response?.data?.detail;
            setPwError(typeof detail === "string" ? detail : "Could not change the password.");
        } finally {
            setSavingPw(false);
        }
    };

    return (
        <AppShell>
            <div className="mx-auto max-w-2xl space-y-8">
                <header>
                    <div className="text-overline mb-2 text-primary">Settings</div>
                    <h1 className="text-display">Your account</h1>
                </header>

                <section className="slip sm:p-8" aria-labelledby="profile-heading">
                    <h2 id="profile-heading" className="text-2xl">Profile</h2>
                    <form onSubmit={saveName} className="mt-4 space-y-4" data-testid="profile-form">
                        <div className="space-y-2">
                            <Label htmlFor="account-name">Display name</Label>
                            <Input id="account-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} data-testid="account-name-input" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="account-email">Email</Label>
                            <Input id="account-email" value={user?.email || ""} readOnly disabled />
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            Role <Badge variant="secondary" className="capitalize">{user?.role}</Badge>
                        </div>
                        <Button type="submit" disabled={savingName || !name.trim() || name.trim() === user?.name} data-testid="save-name-btn">
                            {savingName ? "Saving…" : "Save name"}
                        </Button>
                    </form>
                </section>

                <section className="slip sm:p-8" aria-labelledby="password-heading">
                    <h2 id="password-heading" className="text-2xl">Change password</h2>
                    <form onSubmit={savePassword} className="mt-4 space-y-4" data-testid="password-form">
                        <div className="space-y-2">
                            <Label htmlFor="current-password">Current password</Label>
                            <PasswordInput id="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" required data-testid="current-password-input" />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="account-new-password">New password</Label>
                            <PasswordInput id="account-new-password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" minLength={8} required data-testid="new-password-input" />
                            <p className="text-sm text-muted-foreground">At least 8 characters.</p>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="account-confirm-password">Confirm new password</Label>
                            <PasswordInput id="account-confirm-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" minLength={8} required data-testid="confirm-password-input" />
                        </div>
                        {pwError && (
                            <div role="alert" className="rounded-[var(--r)] border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive" data-testid="password-error">
                                {pwError}
                            </div>
                        )}
                        <Button type="submit" disabled={savingPw} data-testid="change-password-btn">
                            {savingPw ? "Saving…" : "Change password"}
                        </Button>
                    </form>
                </section>
            </div>
        </AppShell>
    );
}
