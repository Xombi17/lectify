import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PenNib, Eye, EyeSlash, Check } from "@/components/icons";
import ThemeToggle from "@/components/ThemeToggle";
import { toast } from "sonner";
import { usePageTitle } from "@/lib/usePageTitle";

export default function AuthPage({ mode }) {
    const isSignup = mode === "signup";
    const { login, signup } = useAuth();
    const router = useRouter();
    usePageTitle(isSignup ? "Create account" : "Sign in");
    const [submitting, setSubmitting] = useState(false);
    const [showPw, setShowPw] = useState(false);
    // The API client sends people here with ?expired=1 when their session can no longer be refreshed
    const expired = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("expired") === "1";
    const [form, setForm] = useState({
        name: "",
        email: "",
        password: "",
        role: "student",
    });

    const update = (k) => (e) => setForm({ ...form, [k]: e.target.value });

    const submit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            // Public signup is student-only; teacher/admin accounts are created by an administrator
            const u = isSignup ? await signup({ ...form, role: "student" }) : await login(form);
            toast.success(isSignup ? "Welcome to Lectify" : `Welcome back, ${u.name}`);
            const params = new URLSearchParams(window.location.search);
            const redirect = params.get("redirect");
            const dashboards = {
                teacher: "/teacher/dashboard",
                student: "/student/dashboard",
                admin: "/admin/dashboard",
            };
            router.push(redirect || dashboards[u.role] || "/");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Something went wrong");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="flex min-h-screen flex-col">
            <header className="desk-bar">
                <Link href="/" className="brand" data-testid="brand-link-auth">
                    <span className="brand-mark"><PenNib size="1em" weight="bold" /></span>
                    Lectify
                </Link>
                <ThemeToggle />
            </header>

            <main id="main" className="book flex-1">
                <div className="page grid items-stretch gap-12 !min-h-0 lg:grid-cols-2 lg:gap-16">
                    <div>
                        <h1 className="text-display font-display">
                            {isSignup ? "Create account" : "Log in"}
                        </h1>
                        <p className="hand text-primary mt-2 text-2xl">
                            {isSignup ? "your lectures, sorted" : "pick up where you left off"}
                        </p>

                        {expired && !isSignup && (
                            <div
                                role="alert"
                                data-testid="session-expired-banner"
                                className="mt-6 rounded-[var(--r)] border border-border bg-muted px-4 py-3 text-sm"
                            >
                                Your session expired. Sign in again and we&apos;ll take you back to where you were.
                            </div>
                        )}

                        <form onSubmit={submit} className="mt-8 grid max-w-[420px] gap-6" data-testid="auth-form">
                            {isSignup && (
                                <div className="grid gap-2">
                                    <Label htmlFor="name">Full name</Label>
                                    <Input
                                        id="name"
                                        data-testid="signup-name-input"
                                        placeholder="Aanya Sharma"
                                        value={form.name}
                                        onChange={update("name")}
                                        required
                                    />
                                </div>
                            )}
                            <div className="grid gap-2">
                                <Label htmlFor="email">Email</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    data-testid="auth-email-input"
                                    placeholder="you@college.edu"
                                    value={form.email}
                                    onChange={update("email")}
                                    required
                                />
                            </div>
                            <div className="grid gap-2">
                                <div className="flex items-center justify-between">
                                    <Label htmlFor="password">Password</Label>
                                    {!isSignup && (
                                        <Link
                                            href="/forgot-password"
                                            data-testid="forgot-password-link"
                                            className="inline-flex min-h-11 items-center text-sm font-bold text-primary underline decoration-2 underline-offset-4"
                                        >
                                            Forgot password?
                                        </Link>
                                    )}
                                </div>
                                <div className="relative">
                                    <Input
                                        id="password"
                                        type={showPw ? "text" : "password"}
                                        data-testid="auth-password-input"
                                        placeholder="••••••••"
                                        autoComplete={isSignup ? "new-password" : "current-password"}
                                        value={form.password}
                                        onChange={update("password")}
                                        required
                                        minLength={isSignup ? 8 : undefined}
                                        className="pr-11"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPw((v) => !v)}
                                        aria-label={showPw ? "Hide password" : "Show password"}
                                        aria-pressed={showPw}
                                        data-testid="toggle-password-btn"
                                        className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-muted-foreground hover:text-foreground"
                                    >
                                        {showPw ? <EyeSlash size={18} /> : <Eye size={18} />}
                                    </button>
                                </div>
                                {isSignup && (
                                    <p className="text-sm text-muted-foreground">At least 8 characters.</p>
                                )}
                            </div>

                            {isSignup && (
                                <p className="text-sm text-muted-foreground" data-testid="signup-student-note">
                                    This creates a student account. Teachers and administrators get their
                                    accounts from their institution.
                                </p>
                            )}

                            <Button
                                type="submit"
                                variant="pen"
                                disabled={submitting}
                                data-testid="auth-submit-btn"
                                className="w-full sm:w-auto"
                            >
                                {submitting ? "Just a moment…" : isSignup ? "Create account" : "Log in"}
                            </Button>
                        </form>

                        <p className="mt-6 text-base text-muted-foreground">
                            {isSignup ? "Already have an account?" : "New here?"}{" "}
                            <Link
                                href={isSignup ? "/login" : "/signup"}
                                data-testid="auth-switch-link"
                                className="inline-flex min-h-11 items-center font-bold text-primary underline decoration-2 underline-offset-4"
                            >
                                {isSignup ? "Log in" : "Create account"}
                            </Link>
                        </p>
                    </div>

                    <figure className="hidden flex-col justify-between gap-12 rounded-[16px] border border-border bg-muted p-10 lg:flex xl:p-12">
                        <blockquote className="text-section max-w-[18ch]">
                            Every lecture, <mark className="hl">searchable</mark>, structured, and study-ready.
                        </blockquote>
                        <ul className="grid gap-3 text-base text-muted-foreground">
                            {["Transcribed and written up the same day", "Notes, a quiz and flashcards for every class", "Search across everything you are enrolled in"].map((t) => (
                                <li key={t} className="flex items-center gap-3">
                                    <Check size={16} weight="bold" className="shrink-0 text-primary" aria-hidden="true" />
                                    {t}
                                </li>
                            ))}
                        </ul>
                    </figure>
                </div>
            </main>

            <footer className="desk-bar mt-6 text-overline text-muted-foreground">
                <div>© {new Date().getFullYear()} Lectify</div>
            </footer>
        </div>
    );
}
