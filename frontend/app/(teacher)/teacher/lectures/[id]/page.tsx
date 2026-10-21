"use client";

import { Suspense } from "react";
import LectureDetailPage from "@/cra-pages/LectureDetailPage";

export default function TeacherLectureDetailPage() {
  return (
    <Suspense fallback={<div role="status" aria-busy="true" aria-label="Loading" className="grid gap-4 p-4">
          <span className="sk w-2/3" />
          <span className="sk w-full" />
          <span className="sk w-1/2" />
        </div>}>
      <LectureDetailPage />
    </Suspense>
  );
}