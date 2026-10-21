
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
    title: `Lecture ${id} | Lectify`,
    description: "View lecture transcript, AI notes, quiz, and flashcards",
    openGraph: {
      type: "article",
    },
  };
}

export default function StudentLectureDetailPage() {
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