import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GraduationCap, Sparkle, Lightning, Headphones } from "@phosphor-icons/react";
import { toast } from "sonner";

const BG_IMG =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='1000' viewBox='0 0 800 1000'%3E%3Crect fill='%231e3a5f' width='800' height='1000'/%3E%3Ccircle cx='200' cy='300' r='150' fill='%23f5c842' opacity='0.3'/%3E%3Ccircle cx='600' cy='700' r='200' fill='%23f5c842' opacity='0.15'/%3E%3Crect x='300' y='400' width='200' height='300' fill='%23f5c842' opacity='0.08'/%3E%3C/svg%3E";

export default function AuthPage({ mode }) {
    const isSignup = mode === "signup";
    const { login, signup } = useAuth();
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);
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
            const u = isSignup ? await signup(form) : await login(form);
            toast.success(isSignup ? "Welcome to LectureMind" : `Welcome back, ${u.name}`);
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
        <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
            {/* Left: form */}
            <div className="flex flex-col justify-between bg-background p-8 lg:p-14">
                <Link href="/" className="flex items-center gap-2" data-testid="brand-link-auth">
                    <div className="flex h-9 w-9 items-center justify-center bg-primary text-primary-foreground">
                        <GraduationCap size={22} weight="duotone" />
                    </div>
                    <div className="leading-none">
                        <div className="font-display text-base font-bold">LectureMind</div>
                        <div className="text-overline text-muted-foreground">
                            AI Academic OS
                        </div>
                    </div>
                </Link>

                <div className="mx-auto w-full max-w-md py-10">
                    <div className="text-overline mb-3 text-primary">
                        {isSignup ? "Create account" : "Sign in"}
                    </div>
                    <h1 className="font-display text-4xl font-black tracking-tighter sm:text-5xl">
                        {isSignup ? (
                            <>
                                Turn lectures into{" "}
                                <span className="bg-accent px-2">study magic.</span>
                            </>
                        ) : (
                            <>
                                Welcome back to your{" "}
                                <span className="bg-accent px-2">lecture brain.</span>
                            </>
                        )}
                    </h1>
                    <p className="mt-4 text-base text-muted-foreground">
                        {isSignup
                            ? "Upload audio. Get smart notes, quizzes, and flashcards in minutes."
                            : "Continue where you left off."}
                    </p>

                    <form onSubmit={submit} className="mt-8 space-y-5" data-testid="auth-form">
                        {isSignup && (
                            <div className="space-y-2">
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
                        <div className="space-y-2">
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
                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                data-testid="auth-password-input"
                                placeholder="••••••••"
                                value={form.password}
                                onChange={update("password")}
                                required
                                minLength={6}
                            />
                        </div>

                        {isSignup && (
                            <div className="space-y-2">
                                <Label>I am a…</Label>
                                <div className="grid grid-cols-2 gap-2">
                                    {["student", "teacher"].map((r) => (
                                        <button
                                            type="button"
                                            key={r}
                                            data-testid={`role-${r}-btn`}
                                            onClick={() => setForm({ ...form, role: r })}
                                            className={`px-4 py-3 text-sm transition-all ${
                                                form.role === r
                                                    ? "border-2 border-primary bg-primary text-primary-foreground"
                                                    : "border border-border bg-card hover:border-primary/40"
                                            }`}
                                        >
                                            <span className="font-display font-bold capitalize">
                                                {r}
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        <Button
                            type="submit"
                            disabled={submitting}
                            data-testid="auth-submit-btn"
                            className="w-full transition-transform hover:scale-[1.01] active:scale-[0.99]"
                        >
                            {submitting
                                ? "Just a moment…"
                                : isSignup
                                    ? "Create my account"
                                    : "Sign in"}
                        </Button>
                    </form>

                    <p className="mt-6 text-sm text-muted-foreground">
                        {isSignup ? "Already onboard?" : "New here?"}{" "}
                        <Link
                            href={isSignup ? "/login" : "/signup"}
                            data-testid="auth-switch-link"
                            className="font-semibold text-primary underline-offset-4 hover:underline"
                        >
                            {isSignup ? "Sign in instead" : "Create an account"}
                        </Link>
                    </p>
                </div>

                <footer className="text-overline text-muted-foreground">
                    © {new Date().getFullYear()} LectureMind · Built for institutions
                </footer>
            </div>

            {/* Right: visual */}
            <div className="relative hidden overflow-hidden bg-primary lg:block">
                <img
                    src={BG_IMG}
                    alt="Academic poster"
                    className="absolute inset-0 h-full w-full object-cover opacity-95"
                />
                <div className="absolute inset-0 bg-primary/30" />
                <div className="relative z-10 flex h-full flex-col justify-end p-14 text-primary-foreground">
                    <div className="text-overline mb-3 text-accent">
                        Built for the lecture hall
                    </div>
                    <h2 className="font-display text-4xl font-black leading-[1.05] tracking-tighter text-white">
                        Every lecture, instantly searchable, structured, and study-ready.
                    </h2>
                    <div className="mt-8 grid grid-cols-3 gap-4 text-white/90">
                        {[
                            { icon: Headphones, label: "Multilingual transcription" },
                            { icon: Sparkle, label: "AI smart notes" },
                            { icon: Lightning, label: "Quizzes & flashcards" },
                        ].map(({ icon: Icon, label }) => (
                            <div key={label} className="border-l-2 border-accent pl-3">
                                <Icon size={22} weight="duotone" className="mb-2" />
                                <div className="text-overline text-accent">
                                    {label.split(" ")[0]}
                                </div>
                                <div className="text-sm">
                                    {label.split(" ").slice(1).join(" ")}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
