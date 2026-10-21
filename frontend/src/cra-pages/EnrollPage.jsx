import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthCard from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { enrollApi } from "@/lib/api";
import { usePageTitle } from "@/lib/usePageTitle";

/**
 * Landing page for a class QR code: /enroll?token=...
 * Shows which class the QR belongs to, sends signed-out people through login/signup and back,
 * and lets a student join with one click.
 */
export default function EnrollPage() {
    usePageTitle("Join a class");
    const router = useRouter();
    const { user } = useAuth();
    const [token] = useState(() =>
        typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("token") || ""
    );
    const [state, setState] = useState(token ? "loading" : "invalid");
    const [className, setClassName] = useState("");
    const [message, setMessage] = useState("");

    useEffect(() => {
        if (!token) return;
        enrollApi
            .preview(token)
            .then((r) => {
                setClassName(r.class_name || "this class");
                setState("ready");
            })
            .catch((err) => {
                setMessage(err?.response?.data?.detail || "This QR code is not valid.");
                setState("invalid");
            });
    }, [token]);

    const back = `/enroll?token=${encodeURIComponent(token)}`;
    const authLink = (path) => `${path}?redirect=${encodeURIComponent(back)}`;

    const join = async () => {
        setState("joining");
        try {
            await enrollApi.join(token);
            setState("joined");
        } catch (err) {
            const status = err?.response?.status;
            setMessage(err?.response?.data?.detail || "Could not join the class.");
            setState(status === 409 ? "already" : "error");
        }
    };

    const dashboard = user?.role === "student" ? "/student/dashboard" : user?.role === "teacher" ? "/teacher/dashboard" : "/admin/dashboard";

    if (state === "loading") {
        return (
            <AuthCard title="Checking your QR code…">
                <span className="sk h-10" aria-busy="true" />
            </AuthCard>
        );
    }
    if (state === "invalid") {
        return (
            <AuthCard title="This QR code can't be used" subtitle={message || "The link is missing or incomplete."}>
                <p className="text-sm text-muted-foreground">
                    QR codes stop working when a teacher generates a new one. Ask your teacher for the current code.
                </p>
                <Button asChild variant="outline" className="mt-6 w-full">
                    <Link href="/">Back to home</Link>
                </Button>
            </AuthCard>
        );
    }
    if (state === "joined" || state === "already") {
        return (
            <AuthCard
                title={state === "joined" ? "You're in!" : "Already enrolled"}
                subtitle={state === "joined" ? `You joined ${className}.` : `You're already part of ${className}.`}
            >
                <Button className="w-full" onClick={() => router.push(dashboard)} data-testid="enroll-done-btn">
                    Go to my library
                </Button>
            </AuthCard>
        );
    }

    // ready / joining / error
    if (!user) {
        return (
            <AuthCard title={`Join ${className}`} subtitle="Sign in or create a student account to join this class.">
                <div className="space-y-3">
                    <Button asChild variant="pen" className="w-full" data-testid="enroll-login-btn">
                        <Link href={authLink("/login")}>Sign in</Link>
                    </Button>
                    <Button asChild variant="outline" className="w-full" data-testid="enroll-signup-btn">
                        <Link href={authLink("/signup")}>Create a student account</Link>
                    </Button>
                </div>
            </AuthCard>
        );
    }
    if (user.role !== "student") {
        return (
            <AuthCard title="Student accounts only" subtitle={`You're signed in as ${user.role}. Only students can join a class with a QR code.`}>
                <Button asChild variant="outline" className="w-full">
                    <Link href={dashboard}>Back to my dashboard</Link>
                </Button>
            </AuthCard>
        );
    }
    return (
        <AuthCard title={`Join ${className}`} subtitle={`Joining as ${user.name}. You'll see this class's lectures in your library.`}>
            {state === "error" && (
                <div role="alert" className="mb-4 rounded-[var(--r)] border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    {message}
                </div>
            )}
            <Button variant="pen" className="w-full" onClick={join} disabled={state === "joining"} data-testid="enroll-join-btn">
                {state === "joining" ? "Joining…" : "Join class"}
            </Button>
        </AuthCard>
    );
}
