import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <p className="text-overline text-primary">Error 404</p>
      <h1 className="font-display text-display">We couldn&apos;t find that page</h1>
      <p className="max-w-md text-base text-muted-foreground">
        The link may be old, or the page may have moved.
      </p>
      <Link
        href="/"
        className="inline-flex min-h-11 items-center rounded-[var(--r)] bg-primary px-5 text-base font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Go to home
      </Link>
    </main>
  );
}
