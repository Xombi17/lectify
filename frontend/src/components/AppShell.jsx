"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
    ArrowRight,
    BookOpen,
    Buildings,
    Brain,
    GraduationCap,
    List,
    Microphone,
    SignOut,
    User,
} from "@phosphor-icons/react";

const NAV_BY_ROLE = {
    teacher: [
        { to: "/teacher/dashboard", label: "Lecture desk", icon: BookOpen },
        { to: "/teacher/upload", label: "Upload lecture", icon: Microphone },
    ],
    student: [
        { to: "/student/dashboard", label: "Library", icon: BookOpen },
        { to: "/student/review", label: "Review queue", icon: Brain },
        { to: "/student/bookmarks", label: "Saved items", icon: List },
    ],
    admin: [{ to: "/admin/dashboard", label: "Academic setup", icon: Buildings }],
};

function isActive(pathname, href) {
    return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppShell({ children }) {
    const { user, logout } = useAuth();
    const router = useRouter();
    const pathname = usePathname() || "";
    const nav = NAV_BY_ROLE[user?.role] || NAV_BY_ROLE.student;
    const home = nav[0]?.to || "/";

    const onLogout = async () => {
        await logout();
        router.push("/login");
    };

    return (
        <div className="app-shell">
            <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:bg-accent focus:px-4 focus:py-3 focus:text-sm focus:font-bold focus:text-accent-foreground">
                Skip to content
            </a>

            <aside className="fixed inset-y-0 left-0 z-40 hidden w-[244px] flex-col bg-[hsl(var(--shell-rail))] text-[hsl(var(--shell-rail-foreground))] md:flex">
                <div className="flex h-20 items-center border-b border-white/10 px-6">
                    <Link href={home} className="flex items-center gap-3" data-testid="brand-link">
                        <span className="flex h-9 w-9 items-center justify-center bg-accent text-accent-foreground">
                            <GraduationCap size={22} weight="bold" />
                        </span>
                        <span>
                            <span className="block font-display text-lg font-extrabold tracking-[-0.05em]">Lectify</span>
                            <span className="block font-mono text-[0.58rem] uppercase tracking-[0.18em] text-white/45">lecture intelligence</span>
                        </span>
                    </Link>
                </div>

                <div className="flex-1 px-3 py-7">
                    <div className="mb-3 px-3 font-mono text-[0.6rem] font-semibold uppercase tracking-[0.18em] text-white/35">
                        {user?.role || "workspace"}
                    </div>
                    <nav aria-label="Primary navigation" className="space-y-1">
                        {nav.map(({ to, label, icon: Icon }) => {
                            const active = isActive(pathname, to);
                            return (
                                <Link
                                    key={to}
                                    href={to}
                                    aria-current={active ? "page" : undefined}
                                    data-testid={`nav-${label.toLowerCase().replace(/\s/g, "-")}`}
                                    className={`group flex items-center justify-between gap-3 border-l-2 px-3 py-3 text-sm transition duration-200 ${
                                        active
                                            ? "border-accent bg-white/10 text-white"
                                            : "border-transparent text-white/60 hover:border-white/30 hover:bg-white/5 hover:text-white"
                                    }`}
                                >
                                    <span className="flex items-center gap-3">
                                        <Icon size={18} weight={active ? "fill" : "regular"} />
                                        {label}
                                    </span>
                                    {active && <ArrowRight size={14} weight="bold" className="text-accent" />}
                                </Link>
                            );
                        })}
                    </nav>
                </div>

                <div className="border-t border-white/10 p-4">
                    <div className="mb-3 flex items-center gap-3 px-2">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/10 text-accent">
                            <User size={16} weight="bold" />
                        </span>
                        <span className="min-w-0">
                            <span className="block truncate text-sm font-semibold" data-testid="user-name">{user?.name || "Workspace user"}</span>
                            <span className="block truncate font-mono text-[0.6rem] uppercase tracking-[0.12em] text-white/45">{user?.role || "member"}</span>
                        </span>
                    </div>
                    <button
                        type="button"
                        onClick={onLogout}
                        data-testid="logout-btn"
                        className="flex w-full items-center gap-3 px-2 py-2 text-left text-xs font-semibold text-white/55 transition hover:text-white"
                    >
                        <SignOut size={16} />
                        Sign out
                    </button>
                </div>
            </aside>

            <div className="md:pl-[244px]">
                <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur">
                    <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-10">
                        <div className="flex items-center gap-3 md:hidden">
                            <Link href={home} className="flex items-center gap-2" data-testid="mobile-brand-link">
                                <span className="flex h-8 w-8 items-center justify-center bg-accent text-accent-foreground"><GraduationCap size={18} weight="bold" /></span>
                                <span className="font-display text-lg font-extrabold tracking-[-0.05em]">Lectify</span>
                            </Link>
                        </div>
                        <div className="hidden items-center gap-2 text-xs text-muted-foreground md:flex">
                            <span className="font-mono uppercase tracking-[0.12em]">workspace</span>
                            <span className="text-border">/</span>
                            <span className="font-semibold text-foreground">{nav.find((item) => isActive(pathname, item.to))?.label || "Overview"}</span>
                        </div>
                        <div className="flex items-center gap-3 md:hidden">
                            <span className="max-w-[9rem] truncate text-sm font-semibold">{user?.name}</span>
                            <button type="button" onClick={onLogout} aria-label="Sign out" className="rounded-full p-2 text-muted-foreground transition hover:bg-muted hover:text-foreground"><SignOut size={18} /></button>
                        </div>
                    </div>
                    <nav aria-label="Mobile navigation" className="shell-mobile-nav">
                        {nav.map(({ to, label }) => {
                            const active = isActive(pathname, to);
                            return <Link key={to} href={to} aria-current={active ? "page" : undefined}>{label}</Link>;
                        })}
                    </nav>
                </header>

                <main id="main-content" className="mx-auto min-h-[calc(100dvh-4rem)] max-w-[1500px] px-4 py-7 sm:px-6 sm:py-10 lg:px-10">
                    {children}
                </main>
            </div>
        </div>
    );
}
