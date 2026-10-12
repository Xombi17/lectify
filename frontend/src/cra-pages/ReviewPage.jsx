import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
    Brain,
    ArrowsClockwise,
    CaretLeft,
    CaretRight,
    Sparkle,
    CheckCircle,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { reviewApi } from "@/lib/api";
import { toast } from "sonner";

const RATINGS = [
    { q: 0, label: "Again", className: "bg-destructive text-destructive-foreground" },
    { q: 1, label: "Hard", className: "bg-muted text-foreground" },
    { q: 2, label: "Good", className: "bg-primary text-primary-foreground" },
    { q: 3, label: "Easy", className: "bg-accent text-accent-foreground" },
];

export default function ReviewPage() {
    const [queue, setQueue] = useState([]);
    const [i, setI] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const [loading, setLoading] = useState(true);
    const [done, setDone] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const due = await reviewApi.due();
            setQueue(due);
            setI(0);
            setFlipped(false);
            setDone(due.length === 0);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
    }, []);

    const rate = async (quality) => {
        const card = queue[i];
        if (!card || submitting) return;
        setSubmitting(true);
        try {
            await reviewApi.submit(card.lecture_id, card.card_index, quality);
            if (i + 1 >= queue.length) {
                setDone(true);
            } else {
                setI(i + 1);
                setFlipped(false);
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Couldn't save review");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="h-64 animate-pulse border border-border bg-muted/40" />
        );
    }

    if (queue.length === 0 || done) {
        return (
            <EmptyState onRefresh={load} reviewed={done && queue.length > 0 ? queue.length : 0} />
        );
    }

    const card = queue[i];
    const progress = Math.round(((i) / queue.length) * 100);

    return (
            <div className="mx-auto max-w-3xl">
                <div className="text-overline mb-3 text-primary">Daily review</div>
                <h1 className="font-display text-4xl font-black tracking-tighter sm:text-5xl">
                    {queue.length - i} card{queue.length - i !== 1 ? "s" : ""} to go.
                </h1>
                <p className="mt-3 text-base text-muted-foreground">
                    Spaced repetition: rate each card after flipping to schedule its next review.
                </p>

                {/* progress */}
                <div className="mt-8 mb-6">
                    <div className="flex items-center justify-between text-xs">
                        <span className="text-overline text-muted-foreground">Progress</span>
                        <span className="font-mono text-primary">
                            {i} / {queue.length}
                        </span>
                    </div>
                    <div className="mt-2 h-2 w-full bg-muted">
                        <div
                            className="h-full bg-primary transition-all duration-500"
                            style={{ width: `${progress}%` }}
                            data-testid="review-progress-bar"
                        />
                    </div>
                </div>

                {/* card meta */}
                <div className="mb-3 flex items-center justify-between">
                    <Link
                        href={`/student/lectures/${card.lecture_id}`}
                        className="text-sm font-bold text-primary underline-offset-4 hover:underline"
                        data-testid="review-card-lecture-link"
                    >
                        {card.lecture_title}
                    </Link>
                    <Badge variant="outline" className="text-xs">
                        {card.repetitions === 0 ? "New" : `Rep ${card.repetitions}`}
                    </Badge>
                </div>

                {/* card */}
                <div className="perspective-1000 mb-6">
                    <motion.div
                        onClick={() => setFlipped(!flipped)}
                        data-testid="review-card"
                        className="preserve-3d relative h-72 w-full cursor-pointer"
                        animate={{ rotateY: flipped ? 180 : 0 }}
                        transition={{ duration: 0.45, ease: "easeInOut" }}
                    >
                        <div className="backface-hidden absolute inset-0 flex flex-col items-center justify-center border-2 border-border bg-card p-8 text-center"
                        style={{ opacity: flipped ? 0 : 1, transition: "opacity 0s linear 0.225s", pointerEvents: flipped ? "none" : "auto" }}>
                            <div className="text-overline mb-3 text-primary">Question</div>
                            <div className="font-display text-2xl font-bold leading-snug tracking-tight">
                                {card.front}
                            </div>
                            <div className="mt-6 flex items-center gap-1 text-xs text-muted-foreground">
                                <ArrowsClockwise size={14} weight="duotone" /> Click to reveal
                            </div>
                        </div>
                        <div className="backface-hidden rotate-y-180 absolute inset-0 flex flex-col items-center justify-center border-2 border-primary bg-accent/20 p-8 text-center"
                        style={{ opacity: flipped ? 1 : 0, transition: "opacity 0s linear 0.225s", pointerEvents: flipped ? "auto" : "none" }}>
                            <div className="text-overline mb-3 text-primary">Answer</div>
                            <div className="font-display text-xl leading-snug tracking-tight">
                                {card.back}
                            </div>
                        </div>
                    </motion.div>
                </div>

                {/* controls */}
                <div className="flex items-center justify-center gap-3">
                    <Button variant="outline" onClick={() => setFlipped(!flipped)}>
                        <ArrowsClockwise size={16} weight="bold" className="mr-2" />
                        {flipped ? "Hide answer" : "Reveal answer"}
                    </Button>
                </div>

                {flipped && (
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-6"
                    >
                        <div className="mb-2 flex items-center justify-center gap-2 text-overline text-muted-foreground">
                            <Brain size={14} weight="duotone" />
                            Rate your recall
                        </div>
                        <div className="grid grid-cols-4 gap-2">
                            {RATINGS.map((r) => (
                                <button
                                    key={r.q}
                                    type="button"
                                    onClick={() => rate(r.q)}
                                    disabled={submitting}
                                    data-testid={`review-rate-${r.label.toLowerCase()}`}
                                    className={`flex flex-col items-center justify-center py-3 transition-all hover:scale-[1.02] disabled:opacity-50 ${r.className}`}
                                >
                                    <span className="font-display text-base font-bold">{r.label}</span>
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}
            </div>
    );
}

function EmptyState({ onRefresh, reviewed }) {
    return (
        <div className="mx-auto max-w-xl border-2 border-dashed border-border bg-card p-12 text-center">
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center bg-accent">
                {reviewed > 0 ? (
                    <CheckCircle size={32} weight="duotone" />
                ) : (
                    <Sparkle size={32} weight="duotone" />
                )}
            </div>
            <h2 className="font-display text-3xl font-black tracking-tighter">
                {reviewed > 0
                    ? `${reviewed} card${reviewed !== 1 ? "s" : ""} reviewed. Nice work.`
                    : "You're all caught up."}
            </h2>
            <p className="mt-3 text-muted-foreground">
                No flashcards are due right now. Come back tomorrow — or open a lecture and
                start a fresh deck.
            </p>
            <div className="mt-6 flex justify-center gap-3">
                <Button variant="outline" onClick={onRefresh} data-testid="review-refresh-btn">
                    <ArrowsClockwise size={14} weight="duotone" className="mr-2" />
                    Refresh
                </Button>
                <Link href="/student/dashboard">
                    <Button>
                        <CaretLeft size={14} weight="bold" /> Back to library
                    </Button>
                </Link>
            </div>
        </div>
    );
}
