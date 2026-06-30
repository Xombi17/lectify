"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
    GraduationCap,
    Microphone,
    Sparkle,
    BookOpen,
    Lightning,
    ChartLine,
    Translate,
    ArrowRight,
} from "@phosphor-icons/react";
import { motion } from "framer-motion";

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-background">
            {/* Nav */}
            <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
                <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
                    <Link href="/" className="flex items-center gap-2" data-testid="landing-brand">
                        <div className="flex h-8 w-8 items-center justify-center bg-primary text-primary-foreground">
                            <GraduationCap size={20} weight="duotone" />
                        </div>
                        <div className="leading-none">
                            <div className="font-display text-base font-bold">LectureMind</div>
                            <div className="text-overline text-muted-foreground">AI Academic OS</div>
                        </div>
                    </Link>
                    <div className="flex items-center gap-2">
                        <Link href="/login" data-testid="landing-login-link">
                            <Button variant="ghost" size="sm">Sign in</Button>
                        </Link>
                        <Link href="/signup" data-testid="landing-signup-link">
                            <Button size="sm" className="transition-transform hover:scale-[1.02]">
                                Get started <ArrowRight size={14} className="ml-1" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </header>

            {/* Hero */}
            <section className="grid-bg relative">
                <div className="mx-auto max-w-6xl px-6 py-24 md:py-32">
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                    >
                        <div className="text-overline mb-4 text-primary">
                            New · AI Lecture Intelligence
                        </div>
                        <h1 className="font-display max-w-4xl text-5xl font-black leading-[0.95] tracking-tighter md:text-7xl">
                            Every lecture, instantly{" "}
                            <span className="bg-accent px-3 leading-tight">study-ready.</span>
                        </h1>
                        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
                            Upload classroom audio. LectureMind transcribes it, strips the filler,
                            and ships smart notes, quizzes, and flashcards in minutes — built for
                            institutions, beloved by students.
                        </p>
                        <div className="mt-10 flex flex-wrap gap-3">
                            <Link href="/signup" data-testid="hero-cta-signup">
                                <Button
                                    size="lg"
                                    className="transition-transform hover:scale-[1.02] active:scale-[0.98]"
                                >
                                    <Microphone size={18} weight="duotone" className="mr-2" />
                                    Start free
                                </Button>
                            </Link>
                            <Link href="/login" data-testid="hero-cta-login">
                                <Button variant="outline" size="lg">
                                    I already have an account
                                </Button>
                            </Link>
                        </div>
                    </motion.div>
                </div>
            </section>

            {/* Features bento */}
            <section className="border-t border-border bg-card">
                <div className="mx-auto max-w-6xl px-6 py-20">
                    <div className="text-overline mb-3 text-primary">What you get</div>
                    <h2 className="font-display mb-10 max-w-3xl text-3xl font-black tracking-tighter md:text-5xl">
                        Not transcription. Educational intelligence.
                    </h2>
                    <div className="grid grid-cols-1 gap-px bg-border md:grid-cols-3">
                        {[
                            {
                                icon: Sparkle,
                                title: "Smart notes",
                                body: "Cleaned, structured bullet notes with definitions, examples, and key concepts.",
                            },
                            {
                                icon: Lightning,
                                title: "Auto quizzes",
                                body: "5+ instant MCQs per lecture with explanations and difficulty grading.",
                            },
                            {
                                icon: BookOpen,
                                title: "Flashcards",
                                body: "Spaced-repetition decks generated from lecture concepts.",
                            },
                            {
                                icon: Translate,
                                title: "Multilingual",
                                body: "Recognises accents and academic terminology — built for global classrooms.",
                            },
                            {
                                icon: ChartLine,
                                title: "Analytics",
                                body: "Track weak topics, quiz performance, and revision frequency.",
                            },
                            {
                                icon: Microphone,
                                title: "Long lectures",
                                body: "Handles 2-hour recordings via intelligent chunking.",
                            },
                        ].map((f, i) => {
                            const Icon = f.icon;
                            return (
                                <div key={i} className="bg-card p-8">
                                    <div className="mb-4 flex h-10 w-10 items-center justify-center bg-primary text-primary-foreground">
                                        <Icon size={20} weight="duotone" />
                                    </div>
                                    <div className="font-display text-lg font-bold tracking-tight">
                                        {f.title}
                                    </div>
                                    <div className="mt-2 text-sm text-muted-foreground">
                                        {f.body}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="border-t border-border bg-primary text-primary-foreground">
                <div className="mx-auto max-w-6xl px-6 py-24 text-center">
                    <h2 className="font-display mx-auto max-w-3xl text-4xl font-black leading-tight tracking-tighter md:text-6xl">
                        Stop taking notes.{" "}
                        <span className="bg-accent px-3 text-accent-foreground">
                            Start understanding.
                        </span>
                    </h2>
                    <div className="mt-10 flex justify-center">
                        <Link href="/signup" data-testid="footer-cta">
                            <Button
                                size="lg"
                                variant="secondary"
                                className="transition-transform hover:scale-[1.02]"
                            >
                                Create your free account <ArrowRight size={16} className="ml-2" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>

            <footer className="border-t border-border bg-background">
                <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-6 text-overline text-muted-foreground">
                    <div>© {new Date().getFullYear()} LectureMind · Academic operating system</div>
                    <div>v0.1 · MVP</div>
                </div>
            </footer>
        </div>
    );
}
