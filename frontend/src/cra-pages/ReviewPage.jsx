import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowsClockwise, CaretLeft } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { reviewApi } from "@/lib/api";
import { toast } from "sonner";

const RATINGS = [
    { q: 0, label: "Again", variant: "default", className: "text-destructive" },
    { q: 1, label: "Hard", variant: "default", className: "" },
    { q: 2, label: "Good", variant: "pen", className: "" },
    { q: 3, label: "Easy", variant: "default", className: "" },
];

export default function ReviewPage() {
    const [queue, setQueue] = useState([]);
    const [i, setI] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const [loading, setLoading] = useState(true);
    const [done, setDone] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const reduce = useReducedMotion();

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
            <div aria-busy="true" aria-label="Loading" className="grid gap-4">
                <span className="sk" />
                <span className="sk" />
                <span className="sk" />
            </div>
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
            <header className="head">
                <h1 className="text-display">Review</h1>
                <span className="font-mono text-base" data-testid="review-counter">
                    {i + 1} / {queue.length}
                </span>
            </header>

            <div
                className="ink-line"
                role="progressbar"
                aria-label="Review progress"
                aria-valuemin={0}
                aria-valuemax={queue.length}
                aria-valuenow={i}
                data-testid="review-progress-bar"
            >
                <span style={{ width: `${progress}%` }} />
            </div>

            <div className="mb-3 flex items-center justify-between">
                <Link
                    href={`/student/lectures/${card.lecture_id}`}
                    className="text-sm font-bold text-primary underline-offset-4 hover:underline"
                    data-testid="review-card-lecture-link"
                >
                    {card.lecture_title}
                </Link>
                <span className="font-mono text-sm text-muted-foreground">
                    {card.repetitions === 0 ? "New" : `Rep ${card.repetitions}`}
                </span>
            </div>

            <motion.div
                key={i}
                initial={reduce ? false : { opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
            >
                <button
                    type="button"
                    className="flip"
                    aria-pressed={flipped}
                    onClick={() => setFlipped(!flipped)}
                    data-testid="review-card"
                >
                    <span className="q">{card.front}</span>
                    <span className="a">{card.back}</span>
                    <span className="text-sm text-muted-foreground">
                        {flipped ? "Answer" : "Click to reveal"}
                    </span>
                </button>
            </motion.div>

            {flipped && (
                <div className="rate !grid-cols-4" role="group" aria-label="Rate your recall">
                    {RATINGS.map((r) => (
                        <Button
                            key={r.q}
                            type="button"
                            variant={r.variant}
                            className={r.className}
                            onClick={() => rate(r.q)}
                            disabled={submitting}
                            data-testid={`review-rate-${r.label.toLowerCase()}`}
                        >
                            {r.label}
                        </Button>
                    ))}
                </div>
            )}
        </div>
    );
}

function EmptyState({ onRefresh, reviewed }) {
    return (
        <div className="empty mx-auto max-w-xl">
            <h2 className="text-2xl font-bold">All caught up</h2>
            <p className="mt-3 text-sm text-muted-foreground">
                {reviewed > 0 ? `${reviewed} card${reviewed !== 1 ? "s" : ""} reviewed. ` : ""}
                No cards are due. New ones appear after your next lecture is ready.
            </p>
            <div className="mt-6 flex justify-center gap-3">
                <Button variant="default" onClick={onRefresh} data-testid="review-refresh-btn">
                    <ArrowsClockwise size={14} weight="bold" className="mr-2" />
                    Refresh
                </Button>
                <Link href="/student/dashboard">
                    <Button variant="quiet">
                        <CaretLeft size={14} weight="bold" /> Back to library
                    </Button>
                </Link>
            </div>
        </div>
    );
}
