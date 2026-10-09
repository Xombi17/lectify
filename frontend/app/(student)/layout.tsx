"use client";

import AppShell from "@/components/AppShell";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!user || user.role !== "student")) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) return <div className="min-h-[100dvh] animate-pulse bg-muted/40" />;
  if (!user || user.role !== "student") {
    return null;
  }

  return <AppShell>{children}</AppShell>;
}