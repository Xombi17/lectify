"use client";

import { Suspense } from "react";
import LectureDetailPage from "@/cra-pages/LectureDetailPage";

export default function TeacherLectureDetailPage() {
  return (
    <Suspense fallback={<div className="h-48 animate-pulse bg-muted/40" />}>
      <LectureDetailPage />
    </Suspense>
  );
}