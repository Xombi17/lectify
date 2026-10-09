"use client";

import AppShell from "@/components/AppShell";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!user || user.role !== "admin")) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) return <div className="min-h-[100dvh] animate-pulse bg-muted/40" />;
  if (!user || user.role !== "admin") {
    return null;
  }

  return <AppShell>{children}</AppShell>;
}