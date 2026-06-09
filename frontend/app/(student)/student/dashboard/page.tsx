"use client";

import { Suspense } from "react";
import StudentDashboard from "@/cra-pages/StudentDashboard";

export default function StudentDashboardPage() {
  return (
    <Suspense fallback={<div className="h-48 animate-pulse bg-muted/40" />}>
      <StudentDashboard />
    </Suspense>
  );
}