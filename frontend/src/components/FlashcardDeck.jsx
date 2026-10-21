import { useState } from "react";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import {
    ArrowsClockwise,
    CaretLeft,
    CaretRight,
    Brain,
} from "@/components/icons";
import { Button } from "@/components/ui/button";
import { reviewApi } from "@/lib/api";
import { toast } from "sonner";

const RATINGS = [
    { q: 0, label: "Again", hint: "1d", className: "bg-destructive text-destructive-foreground" },
    { q: 1, label: "Hard", hint: "≤2d", className: "bg-muted text-foreground" },
    { q: 2, label: "Good", hint: "SR", className: "bg-primary text-primary-foreground" },
    { q: 3, label: "Easy", hint: "long", className: "bg-accent text-accent-foreground" },
];

/**
 * cards: list of {front, back}
 * lectureId: if provided, enables "Rate & schedule" mode (SM-2)
 *            if omitted, falls back to simple flip-only mode
 */
export default function FlashcardDeck({ cards = [], lectureId = null }) {
    const [i, setI] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const [submittingQ, setSubmittingQ] = useState(null);
    const reduce = useReducedMotion();

    if (!cards.length) {
        return (
            <div className="text-sm text-muted-foreground">
                No flashcards generated for this lecture.
            </div>
        );
    }

    const card = cards[i];
    const go = (d) => {
        setFlipped(false);
        setI((prev) => (prev + d + cards.length) % cards.length);
    };

    const rate = async (quality) => {
        if (!lectureId) return;
        setSubmittingQ(quality);
        try {
            await reviewApi.submit(lectureId, i, quality);
            const labels = ["Resetting", "Marked hard", "Scheduled", "Easy — long interval"];
            toast.success(labels[quality]);
            go(1); // advance after rating
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Couldn't save review");
        } finally {
            setSubmittingQ(null);
        }
    };

    return (
        <div className="flex flex-col items-center gap-6">
            <div className="font-mono text-sm text-muted-foreground" data-testid="flashcard-index">
                Card {i + 1} of {cards.length}
            </div>

            <div className="perspective-1000 w-full max-w-2xl">
                <motion.div
                    onClick={() => setFlipped(!flipped)}
                    data-testid="flashcard"
                    className="preserve-3d relative h-72 w-full cursor-pointer"
                    animate={{ rotateY: flipped ? 180 : 0 }}
                    transition={{ duration: reduce ? 0 : 0.45, ease: "easeInOut" }}
                >
                    <div className="backface-hidden absolute inset-0 flex flex-col items-center justify-center rounded-[var(--radius)] border border-border bg-card p-6 text-center"
                        style={{ opacity: flipped ? 0 : 1, transition: reduce ? "none" : "opacity 0s linear 0.225s", pointerEvents: flipped ? "none" : "auto" }}>
                        <div className="text-overline mb-3 text-primary">Question</div>
                        <div className="font-display text-2xl leading-snug">
                            {card.front}
                        </div>
                        <div className="mt-6 flex items-center gap-1 text-sm text-muted-foreground">
                            <ArrowsClockwise size={14} weight="regular" /> Click to flip
                        </div>
                    </div>
                    <div className="backface-hidden rotate-y-180 absolute inset-0 flex flex-col items-center justify-center rounded-[var(--radius)] border border-primary/60 bg-card p-6 text-center"
                        style={{ opacity: flipped ? 1 : 0, transition: reduce ? "none" : "opacity 0s linear 0.225s", pointerEvents: flipped ? "auto" : "none" }}>
                        <div className="text-overline mb-3 text-primary">Answer</div>
                        <div className="font-serif text-lg leading-relaxed">
                            {card.back}
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-3">
                <Button variant="default" onClick={() => go(-1)} data-testid="flashcard-prev-btn">
                    <CaretLeft size={16} weight="bold" /> Prev
                </Button>
                <Button
                    variant="pen"
                    onClick={() => setFlipped(!flipped)}
                    data-testid="flashcard-flip-btn"
                >
                    <ArrowsClockwise size={16} weight="bold" className="mr-2" />
                    Flip
                </Button>
                <Button variant="default" onClick={() => go(1)} data-testid="flashcard-next-btn">
                    Next <CaretRight size={16} weight="bold" />
                </Button>
            </div>

            {/* Spaced-repetition rating row (only if lectureId is set + card flipped) */}
            <AnimatePresence>
                {lectureId && flipped && (
                    <motion.div
                        initial={{ opacity: 0, y: reduce ? 0 : 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: reduce ? 0 : 8 }}
                        className="w-full max-w-2xl"
                    >
                        <div className="mb-2 flex items-center justify-center gap-2 text-overline text-muted-foreground">
                            <Brain size={14} weight="regular" />
                            How well did you know this?
                        </div>
                        <div className="rate" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
                            {RATINGS.map((r) => (
                                <button
                                    key={r.q}
                                    type="button"
                                    onClick={() => rate(r.q)}
                                    disabled={submittingQ !== null}
                                    data-testid={`rate-${r.label.toLowerCase()}-btn`}
                                    className={`flex min-h-11 flex-col items-center justify-center rounded-[var(--r)] px-3 py-2 disabled:opacity-50 motion-safe:transition-transform motion-safe:hover:scale-[1.02] ${r.className}`}
                                >
                                    <span className="text-base font-bold">{r.label}</span>
                                    <span className="text-overline opacity-80">{r.hint}</span>
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
