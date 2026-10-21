"use client";

import { useEffect } from "react";
import Link from "next/link";

// Catches render errors inside any route so a bug shows a recoverable screen instead of a blank page.
export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main
      role="alert"
      className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center"
    >
      <p className="text-overline text-primary">Something went wrong</p>
      <h1 className="font-display text-display">This page hit a problem</h1>
      <p className="max-w-md text-base text-muted-foreground">
        It&apos;s not your fault. Try again, and if it keeps happening go back to the home page.
      </p>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="inline-flex min-h-11 items-center rounded-[var(--r)] bg-primary px-5 text-base font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Try again
        </button>
        <Link href="/" className="inline-flex min-h-11 items-center rounded-[var(--r)] border border-border bg-card px-5 text-base font-medium transition-colors hover:bg-muted">
          Home
        </Link>
      </div>
    </main>
  );
}
