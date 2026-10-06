import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
    GraduationCap,
    SignOut,
    Microphone,
    BookOpen,
    User,
    Brain,
    BookmarkSimple,
    Buildings,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";

export default function AppShell({ children }) {
    const { user, logout } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    const onLogout = () => {
        logout();
        router.push("/login");
    };

    const teacherNav = [
        { to: "/teacher/dashboard", label: "Dashboard", icon: BookOpen },
        { to: "/teacher/upload", label: "New Lecture", icon: Microphone },
    ];
    const studentNav = [
        { to: "/student/dashboard", label: "Library", icon: BookOpen },
        { to: "/student/review", label: "Review", icon: Brain },
        { to: "/student/bookmarks", label: "Bookmarks", icon: BookmarkSimple },
    ];
    const adminNav = [
        { to: "/admin/dashboard", label: "Hierarchy", icon: Buildings },
    ];
    const nav = user?.role === "admin" ? adminNav : user?.role === "teacher" ? teacherNav : studentNav;

    return (
        <div className="min-h-screen bg-background text-foreground selection:bg-accent selection:text-accent-foreground">
            <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
                <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between px-6">
                    <Link
                        href={
                            user?.role === "admin"
                                ? "/admin/dashboard"
                                : user?.role === "teacher"
                                ? "/teacher/dashboard"
                                : "/student/dashboard"
                        }
                        className="flex items-center gap-3 transition-transform active:scale-95"
                        data-testid="brand-link"
                    >
                        <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-primary text-primary-foreground">
                            <GraduationCap size={20} weight="duotone" />
                        </div>
                        <div className="leading-none">
                            <div className="font-display text-base font-bold tracking-tight">
                                LectureMind
                            </div>
                            <div className="text-overline mt-0.5 text-muted-foreground font-mono">
                                OS // {user?.role ? user.role.toUpperCase() : "ACADEMIC"}
                            </div>
                        </div>
                    </Link>

                    <nav className="hidden md:flex items-center gap-2">
                        {nav.map((n) => {
                            const Icon = n.icon;
                            const active = pathname === n.to;
                            return (
                                <Link
                                    key={n.to}
                                    href={n.to}
                                    data-testid={`nav-${n.label.toLowerCase().replace(/\s/g, "-")}`}
                                    className={`group flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-all active:scale-95 ${
                                        active
                                            ? "bg-muted font-bold text-foreground"
                                            : "font-medium text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                                    }`}
                                >
                                    <Icon size={16} weight={active ? "fill" : "duotone"} className={active ? "text-primary" : ""} />
                                    {n.label}
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="flex items-center gap-4">
                        {user && (
                            <div className="flex items-center gap-3 rounded-md border border-border bg-card px-3 py-1.5 shadow-sm">
                                <div className="flex h-6 w-6 items-center justify-center rounded bg-accent/20 text-accent-foreground">
                                    <User size={14} weight="duotone" />
                                </div>
                                <div className="hidden sm:block">
                                    <div className="text-sm font-semibold leading-none" data-testid="user-name">
                                        {user.name}
                                    </div>
                                </div>
                            </div>
                        )}
                        <Button
                            variant="ghost"
                            size="sm"
                            className="font-semibold text-muted-foreground hover:text-destructive"
                            onClick={onLogout}
                            data-testid="logout-btn"
                        >
                            <SignOut size={16} weight="duotone" />
                        </Button>
                    </div>
                </div>
            </header>
            <main className="mx-auto max-w-[1400px] px-6 py-10">{children}</main>
        </div>
    );
}
