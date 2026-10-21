"use client";

import { useEffect, useState } from "react";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/lib/auth";
import { Toaster } from "@/components/ui/sonner";

// BrowserRouter needs `document`, so the CRA-style pages render client-side only.
// ThemeProvider sits outside the mount gate so next-themes' script and context exist from first render.
export default function Providers({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return (
    <ThemeProvider
      attribute="data-theme"
      defaultTheme="system"
      enableSystem
      storageKey="lectify-theme"
      disableTransitionOnChange
    >
      {mounted ? (
        <BrowserRouter>
          <AuthProvider>{children}</AuthProvider>
          <Toaster position="top-right" />
        </BrowserRouter>
      ) : null}
    </ThemeProvider>
  );
}
