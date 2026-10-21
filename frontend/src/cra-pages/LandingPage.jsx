"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import ThemeToggle from "@/components/ThemeToggle";
import {
    PenNib,
    Microphone,
    Sparkle,
    BookOpen,
    Lightning,
    ChartLine,
    Translate,
    ArrowRight,
} from "@/components/icons";
import { motion, useReducedMotion } from "framer-motion";

const FEATURES = [
    { icon: Sparkle, title: "Smart notes", body: "Cleaned, structured notes with definitions, examples, and key concepts." },
    { icon: Lightning, title: "Auto quizzes", body: "5+ instant questions per lecture with explanations and difficulty grading." },
    { icon: BookOpen, title: "Flashcards", body: "Spaced-repetition decks generated from lecture concepts." },
    { icon: Translate, title: "Multilingual", body: "Recognises accents and academic terminology, built for mixed-language classrooms." },
    { icon: ChartLine, title: "Analytics", body: "Track weak topics, quiz performance, and revision frequency." },
    { icon: Microphone, title: "Long lectures", body: "Handles 2-hour recordings by transcribing them whole." },
];

const AUDIENCE = [
    { who: "Students", what: "Revise from clean notes, not a blurry recording." },
    { who: "Teachers", what: "Record the class once. The study kit writes itself." },
    { who: "Institutions", what: "Class-scoped access across every department and batch." },
];

const STEPS = [
    { title: "Upload", body: "Record in class or upload the audio, up to two hours long." },
    { title: "Transcribe & clean", body: "Lectify transcribes the whole lecture and strips out the filler." },
    { title: "Study", body: "Notes, a quiz and flashcards land in the library the same day." },
];

/* Pure HTML/CSS product visual: a transcript fading into the study kit it becomes. */
function LectureMock() {
    return (
        <div
            className="mock"
            role="img"
            aria-label="Example: a lecture transcript turned into structured notes, a quiz and flashcards"
        >
            <div className="mock-bar" aria-hidden="true">
                <span>
                    <span className="mock-dot" />
                    <b>Thermodynamics</b> · Lecture 7
                </span>
                <span>Ready · 4m 12s</span>
            </div>
            <div className="mock-transcript" aria-hidden="true">
                <p>
                    <time>00:14:02</time>
                    So, <s>um, like,</s> entropy is basically the number of ways a system can be arranged.
                </p>
                <p>
                    <time>00:14:31</time>
                    And <s>you know</s> in an isolated system it never goes down. Write that one down.
                </p>
                <p>
                    <time>00:15:08</time>
                    Which is why heat flows from hot to cold, <s>right, so</s> and never the other way.
                </p>
                <p>
                    <time>00:15:40</time>
                    Okay, the second law. Let&apos;s look at a gas in a box.
                </p>
            </div>
            <div className="mock-out" aria-hidden="true">
                <div className="mock-card">
                    <span className="mock-label">
                        <Sparkle size={14} /> Smart notes
                    </span>
                    <div className="mt">Entropy</div>
                    <p>
                        The number of ways a system can be arranged.{" "}
                        <span className="hl">In an isolated system it never decreases.</span>
                    </p>
                </div>
                <div className="mock-card">
                    <span className="mock-label">
                        <Lightning size={14} /> Quiz · 1 of 5
                    </span>
                    <p className="mt-2">Which way does heat flow on its own?</p>
                    <div className="mock-opts">
                        <span className="on">Hot to cold</span>
                        <span>Cold to hot</span>
                    </div>
                </div>
                <div className="mock-card mock-stack">
                    <span className="mock-label">
                        <BookOpen size={14} /> Flashcards · 12 due
                    </span>
                    <p className="mt-1">What can never decrease in an isolated system?</p>
                </div>
            </div>
        </div>
    );
}

export default function LandingPage() {
    const reduce = useReducedMotion();
    // Only the decorative mock fades in; the hero copy is static so it is the LCP and readable without JS.
    const enter = () =>
        reduce
            ? {}
            : {
                  initial: { opacity: 0, y: 8 },
                  animate: { opacity: 1, y: 0 },
                  transition: { duration: 0.3, ease: "easeOut" },
              };

    return (
        <div className="min-h-screen bg-background">
            <header className="topbar">
                <div className="desk-bar">
                    <Link href="/" className="brand" data-testid="landing-brand">
                        <span className="brand-mark" aria-hidden="true">
                            <PenNib size="1em" weight="bold" />
                        </span>
                        Lectify
                    </Link>
                    <nav aria-label="Account" className="shell-actions">
                        <ThemeToggle />
                        <Button asChild variant="quiet" size="sm">
                            <Link href="/login" data-testid="landing-login-link">
                                Log in
                            </Link>
                        </Button>
                        <Button asChild variant="default" size="sm" className="hidden sm:inline-flex">
                            <Link href="/signup" data-testid="landing-signup-link">
                                Create account
                            </Link>
                        </Button>
                    </nav>
                </div>
            </header>

            <main id="main">
                <section className="wrap hero" aria-labelledby="hero-heading">
                    <div>
                        <p className="eyebrow">For every class you sit through</p>
                        <h1 id="hero-heading" className="text-hero mt-4 max-w-[14ch]">
                            Every lecture, instantly <span className="accent-word">study&#8209;ready.</span>
                        </h1>
                        <p className="lede mt-6">
                            Upload class audio. Get clean notes, quizzes and flashcards in minutes.
                        </p>
                        <div className="mt-8 flex flex-wrap gap-3">
                            <Button asChild variant="pen" size="lg">
                            <Link href="/signup" data-testid="hero-cta-signup">
                                Create account <ArrowRight size={16} aria-hidden="true" />
                            </Link>
                        </Button>
                            <Button asChild variant="default" size="lg">
                            <Link href="/login" data-testid="hero-cta-login">
                                Log in
                            </Link>
                        </Button>
                        </div>
                    </div>
                    <motion.div {...enter()}>
                        <LectureMock />
                    </motion.div>
                </section>

                <section className="wrap" aria-labelledby="audience-heading">
                    <h2 id="audience-heading" className="sr-only">
                        Who it is for
                    </h2>
                    <dl className="proof">
                        {AUDIENCE.map(({ who, what }) => (
                            <div key={who}>
                                <dt>{who}</dt>
                                <dd>{what}</dd>
                            </div>
                        ))}
                    </dl>
                </section>

                <section className="wrap section spread" aria-labelledby="features-heading">
                    <header>
                        <p className="eyebrow">What you get</p>
                        <h2 id="features-heading" className="text-section mt-3">
                            One recording in. Six ways to revise out.
                        </h2>
                        <p className="margin-note mt-6">Not transcription alone. Notes you can actually revise from.</p>
                    </header>
                    <ol className="feature-list">
                        {FEATURES.map(({ icon: Icon, title, body }, i) => (
                            <li key={title}>
                                <span className="no" aria-hidden="true">
                                    {String(i + 1).padStart(2, "0")}
                                </span>
                                <h3 className={`t ${i === 0 ? "text-section" : "text-2xl"}`}>{title}</h3>
                                <Icon size={22} className="ic" aria-hidden="true" />
                                <p className="b">{body}</p>
                                {i === 0 && (
                                    <p className="ex">
                                        <b>Entropy:</b> the number of ways a system can be arranged.{" "}
                                        <mark className="hl">In an isolated system it never decreases.</mark>
                                    </p>
                                )}
                            </li>
                        ))}
                    </ol>
                </section>

                <section className="wrap section pt-0" aria-labelledby="how-heading">
                    <p className="eyebrow">How it works</p>
                    <h2 id="how-heading" className="text-section mt-3 max-w-[22ch]">
                        From recording to revision in three steps.
                    </h2>
                    <ol className="steps mt-12">
                        {STEPS.map(({ title, body }, i) => (
                            <li key={title}>
                                <span className="num" aria-hidden="true">
                                    {i + 1}
                                </span>
                                <h3>{title}</h3>
                                <p>{body}</p>
                            </li>
                        ))}
                    </ol>
                </section>

                <section className="cta-band" aria-labelledby="cta-heading">
                    <div className="wrap flex flex-col items-start gap-8 md:flex-row md:items-end md:justify-between">
                        <div>
                            <h2 id="cta-heading" className="text-display max-w-[18ch]">
                                Stop taking notes. Start understanding.
                            </h2>
                            <p className="mt-4 max-w-[48ch]">
                                Create an account and turn your next lecture into a study kit.
                            </p>
                        </div>
                        <Button asChild variant="pen" size="lg" className="btn-on-dark">
                            <Link href="/signup" data-testid="footer-cta">
                                Create account <ArrowRight size={16} aria-hidden="true" />
                            </Link>
                        </Button>
                    </div>
                </section>
            </main>

            <footer className="site-foot">
                <div className="wrap flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="brand" aria-label="Lectify home">
                            <span className="brand-mark" aria-hidden="true">
                                <PenNib size="1em" weight="bold" />
                            </span>
                            Lectify
                        </Link>
                        <span>© {new Date().getFullYear()} Lectify</span>
                    </div>
                    <nav aria-label="Footer" className="flex gap-6">
                        <Link href="/login">Log in</Link>
                        <Link href="/signup">Create account</Link>
                    </nav>
                </div>
            </footer>
        </div>
    );
}
