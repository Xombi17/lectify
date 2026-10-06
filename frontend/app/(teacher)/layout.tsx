"use client";

import AppShell from "@/components/AppShell";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (mounted && !loading && (!user || user.role !== "teacher")) {
      router.push("/");
    }
  }, [user, loading, mounted, router]);

  // Render null on server + first client paint so hydration matches,
  // then resolve auth from localStorage after mount.
  if (!mounted || loading) return null;
  if (!user || user.role !== "teacher") {
    return null;
  }

  return <AppShell>{children}</AppShell>;
}
