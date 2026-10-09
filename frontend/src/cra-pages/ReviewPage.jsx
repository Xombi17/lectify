"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowsClockwise, Brain, CaretLeft, CheckCircle, Sparkle } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { reviewApi } from "@/lib/api";
import { toast } from "sonner";

const RATINGS = [
    { q: 0, label: "Again", className: "bg-destructive text-destructive-foreground" },
    { q: 1, label: "Hard", className: "bg-muted text-foreground" },
    { q: 2, label: "Good", className: "bg-[hsl(var(--success))] text-white" },
    { q: 3, label: "Easy", className: "bg-accent text-accent-foreground" },
];

export default function ReviewPage() {
    const [queue, setQueue] = useState([]);
    const [index, setIndex] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const [loading, setLoading] = useState(true);
    const [done, setDone] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const due = await reviewApi.due();
            setQueue(due);
            setIndex(0);
            setFlipped(false);
            setDone(due.length === 0);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { load(); }, []);

    const rate = async (quality) => {
        const card = queue[index];
        if (!card || submitting) return;
        setSubmitting(true);
        try {
            await reviewApi.submit(card.lecture_id, card.card_index, quality);
            if (index + 1 >= queue.length) setDone(true);
            else {
                setIndex((current) => current + 1);
                setFlipped(false);
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Couldn't save review");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <div className="h-72 animate-pulse border border-border bg-card" />;
    if (queue.length === 0 || done) return <EmptyState onRefresh={load} reviewed={done && queue.length > 0 ? queue.length : 0} />;

    const card = queue[index];
    const progress = Math.round((index / queue.length) * 100);

    return (
        <div className="mx-auto max-w-3xl animate-in">
            <div className="page-intro"><div><div className="eyebrow text-accent">Daily review</div><h1>{queue.length - index} card{queue.length - index !== 1 ? "s" : ""} to go.</h1><p>Reveal each answer, then rate how well you remembered it.</p></div><Link href="/student/dashboard" className="hidden text-sm font-semibold text-muted-foreground underline decoration-border underline-offset-4 hover:text-foreground sm:block">Back to library</Link></div>

            <div className="mb-6 flex items-center justify-between"><span className="eyebrow text-muted-foreground">Queue progress</span><span className="font-mono text-xs text-accent">{index} / {queue.length}</span></div>
            <div className="mb-8 h-1.5 w-full bg-muted"><div className="h-full bg-accent transition-all duration-500" style={{ width: `${progress}%` }} data-testid="review-progress-bar" /></div>

            <div className="mb-3 flex items-center justify-between gap-4"><Link href={`/student/lectures/${card.lecture_id}`} className="truncate text-sm font-bold text-foreground underline decoration-accent underline-offset-4 hover:text-accent" data-testid="review-card-lecture-link">{card.lecture_title}</Link><Badge variant="outline" className="shrink-0 font-mono text-[0.62rem] uppercase">{card.repetitions === 0 ? "New" : `Rep ${card.repetitions}`}</Badge></div>

            <div className="perspective-1000 mb-6">
                <motion.div onClick={() => setFlipped((value) => !value)} data-testid="review-card" className="preserve-3d relative h-80 w-full cursor-pointer" animate={{ rotateY: flipped ? 180 : 0 }} transition={{ duration: 0.55, type: "spring", stiffness: 90 }}>
                    <div className="backface-hidden absolute inset-0 flex flex-col items-center justify-center border border-border bg-card p-8 text-center shadow-[0_16px_40px_hsl(218_28%_13%_/_0.08)]"><div className="eyebrow text-accent">Question</div><div className="mt-6 max-w-2xl font-display text-2xl font-extrabold leading-tight tracking-[-0.05em]">{card.front}</div><div className="mt-8 flex items-center gap-2 font-mono text-[0.62rem] uppercase tracking-[0.1em] text-muted-foreground"><ArrowsClockwise size={14} weight="bold" /> click to reveal</div></div>
                    <div className="backface-hidden rotate-y-180 absolute inset-0 flex flex-col items-center justify-center border border-accent bg-accent/10 p-8 text-center"><div className="eyebrow text-accent">Answer</div><div className="mt-6 max-w-2xl font-display text-xl font-bold leading-snug">{card.back}</div></div>
                </motion.div>
            </div>

            <div className="flex justify-center"><Button variant="outline" onClick={() => setFlipped((value) => !value)}><ArrowsClockwise size={16} weight="bold" /> {flipped ? "Hide answer" : "Reveal answer"}</Button></div>
            {flipped && <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-7"><div className="mb-3 text-center"><div className="eyebrow text-muted-foreground"><Brain size={14} className="mr-1 inline" weight="bold" /> Rate your recall</div></div><div className="grid grid-cols-4 gap-px overflow-hidden border border-border bg-border">{RATINGS.map((rating) => <button key={rating.q} type="button" onClick={() => rate(rating.q)} disabled={submitting} data-testid={`review-rate-${rating.label.toLowerCase()}`} className={`min-h-16 font-display text-sm font-extrabold transition hover:brightness-95 active:scale-[0.98] disabled:opacity-50 ${rating.className}`}>{rating.label}</button>)}</div></motion.div>}
        </div>
    );
}

function EmptyState({ onRefresh, reviewed }) {
    return <div className="empty-panel mx-auto max-w-xl animate-in"><div className="mx-auto flex h-14 w-14 items-center justify-center bg-accent text-accent-foreground">{reviewed > 0 ? <CheckCircle size={28} weight="bold" /> : <Sparkle size={28} weight="duotone" />}</div><h2 className="mt-5 text-3xl font-extrabold tracking-[-0.06em]">{reviewed > 0 ? `${reviewed} card${reviewed !== 1 ? "s" : ""} reviewed.` : "You’re all caught up."}</h2><p className="mx-auto mt-3 max-w-md text-sm leading-7 text-muted-foreground">No flashcards are due right now. Revisit a lecture to start a fresh deck.</p><div className="mt-7 flex justify-center gap-3"><Button variant="outline" onClick={onRefresh} data-testid="review-refresh-btn"><ArrowsClockwise size={15} weight="bold" /> Refresh</Button><Link href="/student/dashboard"><Button><CaretLeft size={15} weight="bold" /> Library</Button></Link></div></div>;
}
