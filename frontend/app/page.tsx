import type { Metadata } from "next";
import { Suspense } from "react";
import LandingPage from "@/cra-pages/LandingPage";

export const metadata: Metadata = {
  title: "Lectify — Lecture intelligence",
  description:
    "Turn lecture recordings into structured notes, quizzes, and flashcards.",
  openGraph: {
    title: "Lectify",
    description: "Lecture intelligence for students and teachers",
    type: "website",
  },
};

export default function LandingPageWrapper() {
  return (
    <Suspense fallback={<div className="h-48 animate-pulse bg-muted/40" />}>
      <LandingPage />
    </Suspense>
  );
}