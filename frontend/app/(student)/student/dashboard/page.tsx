"use client";

import { Suspense } from "react";
import StudentDashboard from "@/cra-pages/StudentDashboard";

export default function StudentDashboardPage() {
  return (
    <Suspense fallback={<div role="status" aria-busy="true" aria-label="Loading" className="grid gap-4 p-4">
          <span className="sk w-2/3" />
          <span className="sk w-full" />
          <span className="sk w-1/2" />
        </div>}>
      <StudentDashboard />
    </Suspense>
  );
}