"use client";

import { Suspense } from "react";
import TeacherDashboard from "@/cra-pages/TeacherDashboard";

export default function TeacherDashboardPage() {
  return (
    <Suspense fallback={<div role="status" aria-busy="true" aria-label="Loading" className="grid gap-4 p-4">
          <span className="sk w-2/3" />
          <span className="sk w-full" />
          <span className="sk w-1/2" />
        </div>}>
      <TeacherDashboard />
    </Suspense>
  );
}