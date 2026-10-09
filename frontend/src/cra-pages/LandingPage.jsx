"use client";

import Link from "next/link";
import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, BookOpen, Checks, GraduationCap, Microphone, Pause, Play, Sparkle } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";

const PIPELINE = [
    { number: "01", title: "Capture the lecture", body: "Upload the recording when class ends. Long sessions stay asynchronous, so your browser is not the bottleneck.", icon: Microphone },
    { number: "02", title: "Clean the signal", body: "The transcript is structured around the ideas that matter, with the original recording kept close by for context.", icon: Sparkle },
    { number: "03", title: "Study the material", body: "Open notes, quizzes, flashcards, search, and transcript from the same lecture workspace.", icon: BookOpen },
];

function StudyPreview() {
    const [playing, setPlaying] = useState(false);

    return (
        <div className="surface-panel overflow-hidden bg-card">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
                <div className="flex items-center gap-3">
                    <button type="button" onClick={() => setPlaying((value) => !value)} aria-label={playing ? "Pause sample recording" : "Play sample recording"} className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-accent-foreground transition hover:scale-105 active:scale-95">
                        {playing ? <Pause size={17} weight="fill" /> : <Play size={17} weight="fill" className="ml-0.5" />}
                    </button>
                    <div>
                        <div className="font-mono text-xs font-semibold">lecture_04 / neural networks</div>
                        <div className="mt-1 font-mono text-[0.62rem] text-muted-foreground">14:22 / sample workspace</div>
                    </div>
                </div>
                <span className="status-chip border-[hsl(var(--success)/.35)] bg-[hsl(var(--success)/.08)] text-[hsl(var(--success))]"><Checks size={13} weight="bold" /> ready</span>
            </div>

            <div className="grid gap-0 lg:grid-cols-[1fr_0.85fr]">
                <div className="border-b border-border p-6 lg:border-b-0 lg:border-r">
                    <div className="eyebrow text-muted-foreground">clean transcript</div>
                    <div className="mt-5 space-y-4">
                        <div className="grid grid-cols-[46px_1fr] gap-4">
                            <span className="font-mono text-[0.68rem] text-muted-foreground">14:15</span>
                            <p className="text-sm leading-7">Backpropagation works because the <mark className="bg-accent/15 px-1 text-foreground">chain rule</mark> lets us calculate how each weight contributes to the loss.</p>
                        </div>
                        <div className="grid grid-cols-[46px_1fr] gap-4 opacity-45">
                            <span className="font-mono text-[0.68rem] text-muted-foreground">14:42</span>
                            <p className="text-sm leading-7">The board is full. Let&apos;s keep the learning rate example for the next pass.</p>
                        </div>
                    </div>
                </div>
                <div className="bg-muted/35 p-6">
                    <div className="eyebrow text-accent">study asset</div>
                    <div className="mt-5 border border-border bg-card p-4">
                        <div className="flex items-center gap-2 text-sm font-bold"><BookOpen size={17} className="text-accent" weight="bold" /> Flashcard</div>
                        <p className="mt-6 text-sm leading-6">What mathematical rule enables backpropagation?</p>
                        <div className="mt-5 border-t border-border pt-3 font-mono text-xs text-muted-foreground">answer hidden · active recall</div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function LandingPage() {
    return (
        <main className="min-h-[100dvh] bg-background">
            <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
                <div className="mx-auto flex h-[4.5rem] max-w-[1500px] items-center justify-between px-5 sm:px-8 lg:px-12">
                    <Link href="/" className="flex items-center gap-3" data-testid="landing-brand">
                        <span className="flex h-9 w-9 items-center justify-center bg-accent text-accent-foreground"><GraduationCap size={21} weight="bold" /></span>
                        <span><span className="block font-display text-lg font-extrabold tracking-[-0.05em]">Lectify</span><span className="hidden font-mono text-[0.58rem] uppercase tracking-[0.16em] text-muted-foreground sm:block">lecture intelligence</span></span>
                    </Link>
                    <nav className="flex items-center gap-2 sm:gap-4" aria-label="Public navigation">
                        <a href="#workflow" className="hidden px-2 py-2 text-sm font-semibold text-muted-foreground transition hover:text-foreground sm:block">How it works</a>
                        <Link href="/login" data-testid="landing-login-link"><Button variant="ghost" size="sm" className="font-semibold">Sign in</Button></Link>
                        <Link href="/signup" data-testid="landing-signup-link"><Button size="sm" className="font-bold">Create account</Button></Link>
                    </nav>
                </div>
            </header>

            <section className="grid-bg border-b border-border">
                <div className="mx-auto grid min-h-[calc(100dvh-4.5rem)] max-w-[1500px] items-center gap-12 px-5 py-14 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20 lg:px-12 lg:py-20">
                    <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}>
                        <div className="eyebrow text-accent">The lecture stays the source</div>
                        <h1 className="mt-5 max-w-xl text-5xl font-extrabold leading-[0.92] tracking-[-0.075em] sm:text-6xl lg:text-7xl">Turn class time into material you can use.</h1>
                        <p className="mt-7 max-w-xl text-lg leading-8 text-muted-foreground">Lectify keeps the recording, the clean transcript, and the study tools connected for the next time you need the idea.</p>
                        <div className="mt-9 flex flex-wrap items-center gap-3">
                            <Link href="/signup" data-testid="hero-cta-signup"><Button size="lg" className="h-12 px-6 font-bold">Create account <ArrowRight size={18} weight="bold" /></Button></Link>
                            <a href="#workflow" data-testid="hero-cta-demo" className="inline-flex h-12 items-center gap-2 px-3 text-sm font-semibold text-muted-foreground underline decoration-border decoration-2 underline-offset-4 transition hover:text-foreground hover:decoration-accent">See the workflow</a>
                        </div>
                        <div className="mt-12 flex flex-wrap gap-x-7 gap-y-3 border-t border-border pt-5 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground"><span className="flex items-center gap-2"><Checks size={14} className="text-accent" /> class-scoped</span><span className="flex items-center gap-2"><Checks size={14} className="text-accent" /> async by design</span><span className="flex items-center gap-2"><Checks size={14} className="text-accent" /> source-grounded</span></div>
                    </motion.div>

                    <motion.div initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.12, ease: [0.16, 1, 0.3, 1] }}>
                        <StudyPreview />
                    </motion.div>
                </div>
            </section>

            <section id="workflow" className="mx-auto max-w-[1500px] px-5 py-20 sm:px-8 lg:px-12 lg:py-28">
                <div className="max-w-2xl">
                    <h2 className="text-4xl font-extrabold leading-none tracking-[-0.065em] sm:text-5xl">One lecture. Three useful passes.</h2>
                    <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground">The product follows the way a lecture is actually used: capture it, make it legible, then return to the parts worth remembering.</p>
                </div>
                <div className="module-grid mt-12 grid-cols-1 md:grid-cols-3">
                    {PIPELINE.map(({ number, title, body, icon: Icon }) => (
                        <article key={number} className="module-cell min-h-[260px] transition hover:bg-muted/45">
                            <div className="flex items-start justify-between"><span className="font-mono text-xs text-accent">{number}</span><Icon size={23} weight="bold" className="text-accent" /></div>
                            <h3 className="mt-16 text-2xl font-extrabold leading-none tracking-[-0.05em]">{title}</h3>
                            <p className="mt-4 text-sm leading-7 text-muted-foreground">{body}</p>
                        </article>
                    ))}
                </div>
            </section>

            <section className="border-y border-border bg-[hsl(var(--shell-rail))] text-white">
                <div className="mx-auto grid max-w-[1500px] gap-12 px-5 py-20 sm:px-8 lg:grid-cols-[1fr_auto] lg:items-end lg:px-12 lg:py-24">
                    <div><div className="eyebrow text-accent">A better return path</div><h2 className="mt-5 max-w-3xl text-4xl font-extrabold leading-[0.95] tracking-[-0.07em] sm:text-6xl">Stop searching through recordings. Start from the idea.</h2></div>
                    <Link href="/signup" data-testid="footer-cta"><Button size="lg" className="h-12 bg-accent px-6 font-bold text-accent-foreground hover:bg-accent/90">Create account <ArrowRight size={18} weight="bold" /></Button></Link>
                </div>
            </section>

            <footer className="mx-auto flex max-w-[1500px] flex-col gap-3 px-5 py-7 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12"><div className="flex items-center gap-2 font-semibold text-foreground"><GraduationCap size={16} className="text-accent" weight="bold" /> Lectify</div><div className="font-mono uppercase tracking-[0.1em]">lecture intelligence · {new Date().getFullYear()}</div></footer>
        </main>
    );
}
