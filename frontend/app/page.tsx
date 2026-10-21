import type { Metadata } from "next";
import { Suspense } from "react";
import LandingPage from "@/cra-pages/LandingPage";

export const metadata: Metadata = {
  title: "Lectify — AI-Powered Lecture Intelligence",
  description:
    "Upload lectures, get AI-generated notes, quizzes, and flashcards. Study smarter with automatic transcription and smart study materials.",
  openGraph: {
    title: "Lectify",
    description: "AI-powered lecture intelligence platform",
    type: "website",
  },
};

export default function LandingPageWrapper() {
  return (
    <Suspense fallback={<div role="status" aria-busy="true" aria-label="Loading" className="grid gap-4 p-4">
          <span className="sk w-2/3" />
          <span className="sk w-full" />
          <span className="sk w-1/2" />
        </div>}>
      <LandingPage />
    </Suspense>
  );
}