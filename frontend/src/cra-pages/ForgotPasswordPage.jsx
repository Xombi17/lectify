import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthCard from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { usePageTitle } from "@/lib/usePageTitle";

/** Accepts a whole pasted reset link or just the token. */
export function extractResetToken(text) {
    const value = (text || "").trim();
    if (!value) return "";
    try {
        const t = new URL(value, "http://placeholder.invalid").searchParams.get("token");
        if (t) return t;
    } catch {
        // not a URL: treat the input as the raw token
    }
    return value;
}

export default function ForgotPasswordPage() {
    usePageTitle("Forgot password");
    const router = useRouter();
    const [link, setLink] = useState("");

    const submit = (e) => {
        e.preventDefault();
        const token = extractResetToken(link);
        if (!token) {
            toast.error("Paste the reset link your administrator gave you");
            return;
        }
        router.push(`/reset-password?token=${encodeURIComponent(token)}`);
    };

    return (
        <AuthCard
            title="Forgot your password?"
            subtitle="Passwords are reset by your institution's administrator."
            footer={
                <>
                    Remembered it?{" "}
                    <Link href="/login" className="inline-flex min-h-11 items-center font-bold text-primary underline-offset-4 hover:underline">
                        Sign in
                    </Link>
                </>
            }
        >
            <ol className="space-y-2 text-sm text-muted-foreground" data-testid="forgot-steps">
                <li>
                    <span className="font-bold text-foreground">1.</span> Ask your administrator for a password
                    reset link (they create it from Admin → Users).
                </li>
                <li>
                    <span className="font-bold text-foreground">2.</span> Open the link, or paste it below. It is
                    valid for 30 minutes and works once.
                </li>
            </ol>
            <form onSubmit={submit} className="mt-6 space-y-4" data-testid="forgot-form">
                <div className="space-y-2">
                    <Label htmlFor="reset-link">Reset link</Label>
                    <Input
                        id="reset-link"
                        value={link}
                        onChange={(e) => setLink(e.target.value)}
                        placeholder="Paste the link here"
                        autoComplete="off"
                        data-testid="reset-link-input"
                    />
                </div>
                <Button type="submit" variant="pen" className="w-full" data-testid="forgot-continue-btn">
                    Continue
                </Button>
            </form>
        </AuthCard>
    );
}
