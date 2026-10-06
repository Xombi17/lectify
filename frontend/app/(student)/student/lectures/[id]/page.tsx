
import type { Metadata } from "next";
import { Suspense } from "react";
import LectureDetailPage from "@/cra-pages/LectureDetailPage";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Lecture ${id} | LectureMind AI`,
    description: "View lecture transcript, AI notes, quiz, and flashcards",
    openGraph: {
      type: "article",
    },
  };
}

export default function StudentLectureDetailPage() {
  return (
    <Suspense fallback={<div className="h-48 animate-pulse bg-muted/40" />}>
      <LectureDetailPage />
    </Suspense>
  );
}