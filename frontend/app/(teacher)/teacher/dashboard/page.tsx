"use client";

import { Suspense } from "react";
import TeacherDashboard from "@/cra-pages/TeacherDashboard";

export default function TeacherDashboardPage() {
  return (
    <Suspense fallback={<div className="h-48 animate-pulse bg-muted/40" />}>
      <TeacherDashboard />
    </Suspense>
  );
}