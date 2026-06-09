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
      router.push("/");
    }
  }, [user, loading, router]);

  if (loading) return null;
  if (!user || user.role !== "student") {
    return null;
  }

  return <AppShell>{children}</AppShell>;
}