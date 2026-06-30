import type { Metadata } from "next";
import { Suspense } from "react";
import LandingPage from "@/cra-pages/LandingPage";

export const metadata: Metadata = {
  title: "LectureMind AI — AI-Powered Lecture Intelligence",
  description:
    "Upload lectures, get AI-generated notes, quizzes, and flashcards. Study smarter with automatic transcription and smart study materials.",
  openGraph: {
    title: "LectureMind AI",
    description: "AI-powered lecture intelligence platform",
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