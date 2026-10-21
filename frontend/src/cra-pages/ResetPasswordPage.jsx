import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthCard from "@/components/AuthCard";
import PasswordInput from "@/components/PasswordInput";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api";
import { toast } from "sonner";
import { usePageTitle } from "@/lib/usePageTitle";

export default function ResetPasswordPage() {
    usePageTitle("Reset password");
    const router = useRouter();
    const [token] = useState(() =>
        typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("token") || ""
    );
    const [password, setPassword] = useState("");
    const [confirm, setConfirm] = useState("");
    const [error, setError] = useState("");
    const [saving, setSaving] = useState(false);

    const submit = async (e) => {
        e.preventDefault();
        setError("");
        if (password !== confirm) {
            setError("The two passwords don't match.");
            return;
        }
        setSaving(true);
        try {
            await authApi.resetPassword(token, password);
            toast.success("Password updated. Sign in with your new password.");
            router.push("/login");
        } catch (err) {
            const detail = err?.response?.data?.detail;
            setError(typeof detail === "string" ? detail : "Could not reset the password. Ask for a new link.");
        } finally {
            setSaving(false);
        }
    };

    if (!token) {
        return (
            <AuthCard title="Reset link missing" subtitle="This page needs a reset link from your administrator.">
                <Button asChild className="w-full">
                    <Link href="/forgot-password">How to get a reset link</Link>
                </Button>
            </AuthCard>
        );
    }

    return (
        <AuthCard title="Choose a new password" subtitle="Use at least 8 characters.">
            <form onSubmit={submit} className="space-y-4" data-testid="reset-form">
                <div className="space-y-2">
                    <Label htmlFor="new-password">New password</Label>
                    <PasswordInput
                        id="new-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="new-password"
                        minLength={8}
                        required
                        data-testid="reset-password-input"
                    />
                </div>
                <div className="space-y-2">
                    <Label htmlFor="confirm-password">Confirm new password</Label>
                    <PasswordInput
                        id="confirm-password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        autoComplete="new-password"
                        minLength={8}
                        required
                        data-testid="reset-confirm-input"
                    />
                </div>
                {error && (
                    <div role="alert" className="rounded-[var(--r)] border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive" data-testid="reset-error">
                        {error}{" "}
                        <Link href="/forgot-password" className="font-bold underline underline-offset-4">
                            Get a new link
                        </Link>
                    </div>
                )}
                <Button type="submit" variant="pen" disabled={saving} className="w-full" data-testid="reset-submit-btn">
                    {saving ? "Saving…" : "Update password"}
                </Button>
            </form>
        </AuthCard>
    );
}
