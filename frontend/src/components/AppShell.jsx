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
        <div className="min-h-screen bg-background">
            <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
                <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
                    <Link
                        href={
                            user?.role === "admin"
                                ? "/admin/dashboard"
                                : user?.role === "teacher"
                                ? "/teacher/dashboard"
                                : "/student/dashboard"
                        }
                        className="flex items-center gap-2"
                        data-testid="brand-link"
                    >
                        <div className="flex h-8 w-8 items-center justify-center bg-primary text-primary-foreground">
                            <GraduationCap size={20} weight="duotone" />
                        </div>
                        <div className="leading-none">
                            <div className="font-display text-base font-bold tracking-tight">
                                LectureMind
                            </div>
                            <div className="text-overline text-muted-foreground">
                                AI Academic OS
                            </div>
                        </div>
                    </Link>

                    <nav className="hidden items-center gap-1 md:flex">
                        {nav.map((n) => {
                            const Icon = n.icon;
                            const active = pathname === n.to;
                            return (
                                <Link
                                    key={n.to}
                                    href={n.to}
                                    data-testid={`nav-${n.label.toLowerCase().replace(/\s/g, "-")}`}
                                    className={`flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                                        active
                                            ? "border-b-2 border-primary font-semibold text-primary"
                                            : "border-b-2 border-transparent text-muted-foreground hover:text-foreground"
                                    }`}
                                >
                                    <Icon size={16} weight="duotone" />
                                    {n.label}
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="flex items-center gap-3">
                        {user && (
                            <div className="flex items-center gap-2 text-sm">
                                <div className="flex h-8 w-8 items-center justify-center bg-accent/30 text-accent-foreground">
                                    <User size={16} weight="duotone" />
                                </div>
                                <div className="hidden text-right leading-tight sm:block">
                                    <div className="font-medium" data-testid="user-name">
                                        {user.name}
                                    </div>
                                    <div className="text-overline text-muted-foreground">
                                        {user.role}
                                    </div>
                                </div>
                            </div>
                        )}
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onLogout}
                            data-testid="logout-btn"
                        >
                            <SignOut size={16} weight="duotone" />
                            <span className="ml-2 hidden sm:inline">Sign out</span>
                        </Button>
                    </div>
                </div>
            </header>
            <main className="mx-auto max-w-7xl px-6 py-10">{children}</main>
        </div>
    );
}
