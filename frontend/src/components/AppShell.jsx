import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
    PenNib,
    SignOut,
    Microphone,
    BookOpen,
    User,
    Brain,
    BookmarkSimple,
    Buildings,
    UsersThree,
} from "@/components/icons";
import { Button } from "@/components/ui/button";
import ThemeToggle from "@/components/ThemeToggle";

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
        { to: "/admin/users", label: "Users", icon: UsersThree },
    ];
    const nav = user?.role === "admin" ? adminNav : user?.role === "teacher" ? teacherNav : studentNav;

    const home =
        user?.role === "admin" ? "/admin/dashboard" : user?.role === "teacher" ? "/teacher/dashboard" : "/student/dashboard";

    return (
        <div className="min-h-screen bg-background">
            <header className="topbar">
                <div className="desk-bar">
                    <Link href={home} className="brand" data-testid="brand-link">
                        <span className="brand-mark" aria-hidden="true">
                            <PenNib size="1em" weight="bold" />
                        </span>
                        Lectify
                    </Link>

                    <nav aria-label="Sections" className="tabs">
                        {nav.map((n) => {
                            const Icon = n.icon;
                            const active = pathname === n.to || pathname?.startsWith(n.to + "/");
                            return (
                                <Link
                                    key={n.to}
                                    href={n.to}
                                    data-testid={`nav-${n.label.toLowerCase().replace(/\s/g, "-")}`}
                                    aria-current={active ? "page" : undefined}
                                >
                                    <Icon size={18} aria-hidden="true" />
                                    {n.label}
                                </Link>
                            );
                        })}
                    </nav>

                    <div className="shell-actions">
                        <ThemeToggle />
                        {user && (
                            <Link
                                href="/account"
                                aria-label={`Account settings for ${user.name}`}
                                aria-current={pathname === "/account" ? "page" : undefined}
                                data-testid="account-link"
                                className="flex min-h-11 items-center gap-2 rounded-[var(--r)] px-2 text-sm transition-colors hover:bg-muted aria-[current=page]:bg-muted"
                            >
                                <span className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-muted">
                                    <User size={16} aria-hidden="true" />
                                </span>
                                <span className="hidden text-left leading-tight lg:block">
                                    <span className="block font-medium text-foreground" data-testid="user-name">
                                        {user.name}
                                    </span>
                                    <span className="block text-sm capitalize text-muted-foreground">{user.role}</span>
                                </span>
                            </Link>
                        )}
                        <Button
                            variant="quiet"
                            size="sm"
                            onClick={onLogout}
                            data-testid="logout-btn"
                            className="min-w-11"
                        >
                            <SignOut size={16} aria-hidden="true" />
                            <span className="sr-only sm:not-sr-only">Log out</span>
                        </Button>
                    </div>
                </div>
            </header>
            <main
                id="main"
                tabIndex={-1}
                className={user?.role === "admin" ? "book page page--plain" : "book page"}
            >
                <div key={pathname} className="turn">
                    {children}
                </div>
            </main>
        </div>
    );
}
