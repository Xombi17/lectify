"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
    GraduationCap,
    Microphone,
    Sparkle,
    BookOpen,
    Lightning,
    Translate,
    ArrowRight,
    Play,
    Pause,
    Checks
} from "@phosphor-icons/react";
import { motion } from "framer-motion";
import { useState } from "react";

// Mock trust logos
const TRUSTED_LOGOS = ["Stanford", "MIT", "Oxford", "Cambridge", "ETH Zurich"];

function StudyPreview() {
    const [playing, setPlaying] = useState(false);
    
    return (
        <div className="relative mx-auto w-full max-w-md overflow-hidden rounded-xl border border-border bg-card shadow-2xl">
            <div className="border-b border-border bg-muted/50 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <button 
                        onClick={() => setPlaying(!playing)}
                        className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground transition-all active:scale-95"
                    >
                        {playing ? <Pause weight="fill" /> : <Play weight="fill" className="ml-1" />}
                    </button>
                    <div>
                        <div className="text-sm font-bold font-mono">lec_04_neural_nets.mp3</div>
                        <div className="text-xs text-muted-foreground font-mono">00:14:22 / 01:20:00</div>
                    </div>
                </div>
                <div className="flex items-center gap-1.5 rounded-full border border-border bg-background px-2.5 py-1 text-xs font-medium text-muted-foreground">
                    <Checks size={14} className="text-accent" />
                    Transcribed
                </div>
            </div>
            
            <div className="p-6">
                <div className="space-y-4">
                    <div className="flex gap-4">
                        <div className="mt-1 font-mono text-xs text-muted-foreground">14:15</div>
                        <div className="text-sm leading-relaxed">
                            So when we talk about backpropagation, the key insight is the <span className="bg-accent/30 font-semibold px-1 rounded">chain rule</span> of calculus. It allows us to compute the gradient of the loss function with respect to each weight.
                        </div>
                    </div>
                    <div className="flex gap-4 opacity-50">
                        <div className="mt-1 font-mono text-xs text-muted-foreground">14:42</div>
                        <div className="text-sm leading-relaxed">
                            Um, let me wipe the board... anyway, where were we? Ah right, learning rates.
                        </div>
                    </div>
                </div>
                
                <div className="mt-6 border-t border-border pt-6">
                    <div className="mb-3 text-xs font-bold uppercase tracking-widest text-primary">Generated Asset</div>
                    <div className="rounded-lg border border-border bg-muted/30 p-4">
                        <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
                            <BookOpen weight="duotone" className="text-accent" />
                            Flashcard
                        </div>
                        <div className="text-sm">What mathematical rule enables backpropagation?</div>
                        <div className="mt-3 rounded border border-border/50 bg-background p-2 text-sm font-medium">
                            The Chain Rule
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function LandingPage() {
    return (
        <div className="min-h-screen bg-background">
            <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
                <div className="mx-auto flex h-16 max-w-[1400px] items-center justify-between px-6">
                    <Link href="/" className="flex items-center gap-2" data-testid="landing-brand">
                        <div className="flex h-8 w-8 items-center justify-center bg-primary text-primary-foreground rounded-sm">
                            <GraduationCap size={20} weight="duotone" />
                        </div>
                        <div className="leading-none">
                            <div className="font-display text-base font-bold tracking-tight">LectureMind</div>
                        </div>
                    </Link>
                    <div className="flex items-center gap-3">
                        <Link href="/login" data-testid="landing-login-link">
                            <Button variant="ghost" size="sm" className="font-semibold text-muted-foreground hover:text-foreground">Sign in</Button>
                        </Link>
                        <Link href="/signup" data-testid="landing-signup-link">
                            <Button size="sm" className="font-bold">
                                Launch Studio
                            </Button>
                        </Link>
                    </div>
                </div>
            </header>

            {/* Hero */}
            <section className="relative overflow-hidden border-b border-border grid-bg">
                <div className="mx-auto max-w-[1400px] px-6 py-20 lg:py-32">
                    <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
                        <motion.div
                            initial={{ opacity: 0, y: 24 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                        >
                            <h1 className="font-display max-w-2xl text-5xl font-black leading-[1.05] tracking-tighter md:text-7xl">
                                Turn classroom audio into <span className="bg-accent text-accent-foreground px-2">exam intelligence.</span>
                            </h1>
                            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
                                Upload heavy lecture recordings. We strip the professor's filler and ship structured notes, spaced-repetition flashcards, and instant quizzes directly to your dashboard.
                            </p>
                            <div className="mt-10 flex flex-wrap gap-4">
                                <Link href="/signup" data-testid="hero-cta-signup">
                                    <Button size="lg" className="h-12 px-8 text-base font-bold">
                                        <Microphone size={20} weight="duotone" className="mr-2" />
                                        Launch Studio
                                    </Button>
                                </Link>
                                <Link href="#demo" data-testid="hero-cta-demo">
                                    <Button variant="outline" size="lg" className="h-12 px-8 text-base font-semibold">
                                        See how it works
                                    </Button>
                                </Link>
                            </div>
                        </motion.div>
                        
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                            className="relative lg:block"
                        >
                            <StudyPreview />
                        </motion.div>
                    </div>
                </div>
            </section>
            
            {/* Trust Bar */}
            <section className="border-b border-border bg-muted/30 py-8">
                <div className="mx-auto max-w-[1400px] px-6">
                    <div className="flex flex-wrap items-center justify-center gap-8 text-muted-foreground/60 md:gap-16">
                        {TRUSTED_LOGOS.map((logo) => (
                            <div key={logo} className="font-display text-xl font-bold uppercase tracking-widest">{logo}</div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Asymmetric Bento */}
            <section id="demo" className="bg-background py-24 lg:py-32">
                <div className="mx-auto max-w-[1400px] px-6">
                    <h2 className="font-display mb-16 max-w-2xl text-4xl font-black tracking-tighter md:text-5xl">
                        A rigorous academic pipeline. <br className="hidden md:block"/> No generic AI summaries.
                    </h2>
                    
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-3 lg:grid-cols-4">
                        {/* High density notes */}
                        <div className="col-span-1 flex flex-col justify-between rounded-xl border border-border bg-card p-8 md:col-span-2 lg:col-span-2">
                            <div>
                                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                                    <Sparkle size={24} weight="duotone" />
                                </div>
                                <h3 className="font-display text-2xl font-bold tracking-tight">De-noised Transcripts</h3>
                                <p className="mt-3 max-w-md leading-relaxed text-muted-foreground">
                                    We edit out "umms", administrative rambling, and coughing. You get clean, highly-structured bullet points highlighting definitions and core exam concepts.
                                </p>
                            </div>
                            <div className="mt-8 rounded-lg border border-border bg-muted/40 p-4 font-mono text-xs text-muted-foreground">
                                &gt; processing chunk_01... <br/>
                                &gt; identifying core_concept: Backpropagation <br/>
                                <span className="text-accent font-bold">&gt; tagging priority: HIGH_EXAM_PROBABILITY</span>
                            </div>
                        </div>
                        
                        {/* Flashcards */}
                        <div className="col-span-1 rounded-xl border border-border bg-primary p-8 text-primary-foreground md:col-span-1 lg:col-span-2">
                            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                                <BookOpen size={24} weight="duotone" />
                            </div>
                            <h3 className="font-display text-2xl font-bold tracking-tight text-white">Active Recall Decks</h3>
                            <p className="mt-3 leading-relaxed text-primary-foreground/80">
                                Automatically generated spaced-repetition flashcards ensure you don't just read the notes—you actually retain them for the final.
                            </p>
                        </div>
                        
                        {/* Instant Quizzes */}
                        <div className="col-span-1 rounded-xl border border-border bg-card p-8 md:col-span-1 lg:col-span-2">
                            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-foreground">
                                <Lightning size={24} weight="duotone" />
                            </div>
                            <h3 className="font-display text-2xl font-bold tracking-tight">Instant Quizzes</h3>
                            <p className="mt-3 leading-relaxed text-muted-foreground">
                                Test yourself immediately after the lecture. 5+ multiple-choice questions graded instantly with deep-dive explanations.
                            </p>
                        </div>
                        
                        {/* Multilingual */}
                        <div className="col-span-1 rounded-xl border border-border bg-card p-8 md:col-span-2 lg:col-span-2">
                            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-foreground">
                                <Translate size={24} weight="duotone" />
                            </div>
                            <h3 className="font-display text-2xl font-bold tracking-tight">Global Terminology</h3>
                            <p className="mt-3 leading-relaxed text-muted-foreground">
                                Recognizes heavy accents and specialized academic jargon across medical, engineering, and humanities domains.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Minimal CTA */}
            <section className="border-t border-border bg-primary text-primary-foreground">
                <div className="mx-auto max-w-4xl px-6 py-24 text-center">
                    <h2 className="font-display text-4xl font-black leading-tight tracking-tighter md:text-6xl text-white">
                        Stop taking notes. <br/> Start retaining.
                    </h2>
                    <div className="mt-10 flex justify-center">
                        <Link href="/signup">
                            <Button size="lg" className="h-14 px-10 text-lg font-bold bg-accent text-accent-foreground hover:bg-accent/90">
                                Launch Studio <ArrowRight size={20} className="ml-2" />
                            </Button>
                        </Link>
                    </div>
                </div>
            </section>

            <footer className="border-t border-border bg-background">
                <div className="mx-auto flex max-w-[1400px] flex-col md:flex-row items-center justify-between px-6 py-8 text-sm font-medium text-muted-foreground">
                    <div className="flex items-center gap-2">
                        <GraduationCap size={16} weight="fill" className="text-primary" />
                        © {new Date().getFullYear()} LectureMind
                    </div>
                    <div className="mt-4 md:mt-0 font-mono text-xs">v1.0.0-rc.1 · System Nominal</div>
                </div>
            </footer>
        </div>
    );
}
