"use client";

import { useEffect, useState } from "react";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { Toaster } from "@/components/ui/sonner";

// BrowserRouter needs `document`, so the CRA-style pages render client-side only.
export default function Providers({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;
  return (
    <BrowserRouter>
      <AuthProvider>{children}</AuthProvider>
      <Toaster
        position="top-right"
        toastOptions={{ classNames: { toast: "border border-border bg-card text-foreground" } }}
      />
    </BrowserRouter>
  );
}
