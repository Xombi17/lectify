import Link from "next/link";
import { PenNib } from "@/components/icons";

/** Centered card shell for the small public flows (forgot/reset password, enroll). */
export default function AuthCard({ title, subtitle, children, footer }) {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12 sm:px-6">
            <Link href="/" className="brand mb-6" data-testid="brand-link-auth">
                <span className="brand-mark" aria-hidden="true">
                    <PenNib size="1em" weight="bold" />
                </span>
                Lectify
            </Link>
            <main id="main" className="w-full max-w-md rounded-[var(--radius)] border border-border bg-card p-6 sm:p-10">
                <h1 className="font-display text-display">{title}</h1>
                {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
                <div className="mt-6">{children}</div>
            </main>
            {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
        </div>
    );
}
