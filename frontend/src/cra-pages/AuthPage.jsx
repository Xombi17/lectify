"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowRight, Check, GraduationCap, Headphones, Lightning, Sparkle } from "@phosphor-icons/react";
import { toast } from "sonner";

const FLOW = [
    { icon: Headphones, title: "Record or upload", detail: "Keep the original lecture as the source." },
    { icon: Sparkle, title: "Clean and structure", detail: "Turn the transcript into usable study material." },
    { icon: Lightning, title: "Study with intent", detail: "Review notes, quizzes, and flashcards in one place." },
];

export default function AuthPage({ mode }) {
    const isSignup = mode === "signup";
    const { login, signup } = useAuth();
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");
    const [form, setForm] = useState({ name: "", email: "", password: "", role: "student" });

    const update = (key) => (event) => {
        setError("");
        setForm((current) => ({ ...current, [key]: event.target.value }));
    };

    const submit = async (event) => {
        event.preventDefault();
        setSubmitting(true);
        setError("");
        try {
            const user = isSignup ? await signup(form) : await login(form);
            toast.success(isSignup ? "Account created" : `Welcome back, ${user.name}`);
            const fallback = user.role === "admin" ? "/admin/dashboard" : user.role === "teacher" ? "/teacher/dashboard" : "/student/dashboard";
            const requested = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("redirect") : null;
            const destination = requested?.startsWith("/") && !requested.startsWith("//") ? requested : fallback;
            router.push(destination);
        } catch (err) {
            const message = err?.response?.data?.detail || "We couldn't complete that request. Check your details and try again.";
            setError(message);
            toast.error(message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <main className="min-h-[100dvh] bg-background lg:grid lg:grid-cols-[minmax(0,0.9fr)_minmax(420px,1.1fr)]">
            <section className="flex min-h-[100dvh] flex-col px-6 py-7 sm:px-10 lg:px-16 lg:py-10">
                <Link href="/" className="flex w-fit items-center gap-3" data-testid="brand-link-auth">
                    <span className="flex h-9 w-9 items-center justify-center bg-accent text-accent-foreground"><GraduationCap size={21} weight="bold" /></span>
                    <span>
                        <span className="block font-display text-lg font-extrabold tracking-[-0.05em]">Lectify</span>
                        <span className="block font-mono text-[0.58rem] uppercase tracking-[0.16em] text-muted-foreground">lecture intelligence</span>
                    </span>
                </Link>

                <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-12">
                    <div className="eyebrow text-accent">{isSignup ? "Create your workspace" : "Return to your workspace"}</div>
                    <h1 className="mt-4 text-4xl font-extrabold leading-[0.98] tracking-[-0.06em] sm:text-5xl">
                        {isSignup ? "Make every lecture easier to revisit." : "Pick up where you left off."}
                    </h1>
                    <p className="mt-4 max-w-md text-base leading-7 text-muted-foreground">
                        {isSignup ? "One place for lecture recordings, clean notes, quizzes, and the concepts worth keeping." : "Your class library and review queue are waiting."}
                    </p>

                    <form onSubmit={submit} className="mt-9 space-y-5" data-testid="auth-form">
                        {isSignup && (
                            <div className="space-y-2">
                                <Label htmlFor="name">Full name</Label>
                                <Input id="name" data-testid="signup-name-input" placeholder="Aanya Sharma" value={form.name} onChange={update("name")} autoComplete="name" required />
                            </div>
                        )}
                        <div className="space-y-2">
                            <Label htmlFor="email">College email</Label>
                            <Input id="email" type="email" data-testid="auth-email-input" placeholder="you@college.edu" value={form.email} onChange={update("email")} autoComplete="email" required />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <Input id="password" type="password" data-testid="auth-password-input" placeholder="At least 6 characters" value={form.password} onChange={update("password")} autoComplete={isSignup ? "new-password" : "current-password"} minLength={6} required />
                        </div>

                        {isSignup && (
                            <fieldset className="space-y-2">
                                <legend className="text-sm font-semibold">I am signing up as</legend>
                                <div className="grid grid-cols-2 gap-2">
                                    {["student", "teacher"].map((role) => {
                                        const selected = form.role === role;
                                        return (
                                            <button type="button" key={role} data-testid={`role-${role}-btn`} aria-pressed={selected} onClick={() => setForm((current) => ({ ...current, role }))} className={`flex items-center justify-between border px-4 py-3 text-left text-sm font-semibold capitalize transition ${selected ? "border-accent bg-accent text-accent-foreground" : "border-input bg-card hover:border-accent/60"}`}>
                                                {role}
                                                {selected && <Check size={16} weight="bold" />}
                                            </button>
                                        );
                                    })}
                                </div>
                            </fieldset>
                        )}

                        {error && <p role="alert" data-testid="auth-error" className="border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm leading-6 text-destructive">{error}</p>}

                        <Button type="submit" disabled={submitting} data-testid="auth-submit-btn" className="h-11 w-full font-bold">
                            {submitting ? "Checking details…" : isSignup ? "Create account" : "Sign in"}
                            {!submitting && <ArrowRight size={17} weight="bold" />}
                        </Button>
                    </form>

                    <p className="mt-6 text-sm text-muted-foreground">
                        {isSignup ? "Already have an account?" : "New to Lectify?"}{" "}
                        <Link href={isSignup ? "/login" : "/signup"} data-testid="auth-switch-link" className="font-semibold text-foreground underline decoration-accent decoration-2 underline-offset-4 hover:text-accent">
                            {isSignup ? "Sign in" : "Create an account"}
                        </Link>
                    </p>
                </div>

                <footer className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-muted-foreground">© {new Date().getFullYear()} Lectify</footer>
            </section>

            <aside className="relative hidden overflow-hidden bg-[hsl(var(--shell-rail))] text-white lg:flex lg:flex-col lg:justify-between lg:p-16">
                <div className="absolute right-[-12rem] top-[-12rem] h-[30rem] w-[30rem] rounded-full border-[3rem] border-accent/20" aria-hidden="true" />
                <div className="relative">
                    <div className="eyebrow text-accent">From lecture to study material</div>
                    <h2 className="mt-6 max-w-xl text-5xl font-extrabold leading-[0.96] tracking-[-0.07em] xl:text-6xl">The useful parts of class, kept in one place.</h2>
                    <p className="mt-6 max-w-lg text-base leading-7 text-white/60">Lectify keeps the recording, the cleaned transcript, and the study tools connected so students can return to the exact idea they need.</p>
                </div>
                <div className="relative space-y-3">
                    {FLOW.map(({ icon: Icon, title, detail }, index) => (
                        <div key={title} className="grid grid-cols-[auto_1fr_auto] items-center gap-4 border-t border-white/15 py-5">
                            <span className="flex h-10 w-10 items-center justify-center border border-white/20 text-accent"><Icon size={20} weight="bold" /></span>
                            <span><span className="block font-semibold">{title}</span><span className="mt-1 block text-sm text-white/55">{detail}</span></span>
                            <span className="font-mono text-xs text-white/35">0{index + 1}</span>
                        </div>
                    ))}
                </div>
            </aside>
        </main>
    );
}
