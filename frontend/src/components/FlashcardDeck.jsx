import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowsClockwise, CaretLeft, CaretRight } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";

export default function FlashcardDeck({ cards = [] }) {
    const [i, setI] = useState(0);
    const [flipped, setFlipped] = useState(false);

    if (!cards.length) {
        return <div className="text-sm text-muted-foreground">No flashcards generated for this lecture.</div>;
    }

    const card = cards[i];
    const go = (d) => {
        setFlipped(false);
        setI((prev) => (prev + d + cards.length) % cards.length);
    };

    return (
        <div className="flex flex-col items-center gap-6">
            <div className="text-overline text-muted-foreground" data-testid="flashcard-index">
                Card {i + 1} of {cards.length}
            </div>

            <div className="perspective-1000 w-full max-w-2xl">
                <motion.div
                    onClick={() => setFlipped(!flipped)}
                    data-testid="flashcard"
                    className="preserve-3d relative h-72 w-full cursor-pointer"
                    animate={{ rotateY: flipped ? 180 : 0 }}
                    transition={{ duration: 0.6, type: "spring", stiffness: 90 }}
                >
                    {/* Front */}
                    <div className="backface-hidden absolute inset-0 flex flex-col items-center justify-center border-2 border-border bg-card p-8 text-center">
                        <div className="text-overline mb-3 text-primary">Question</div>
                        <div className="font-display text-2xl font-bold leading-snug tracking-tight">
                            {card.front}
                        </div>
                        <div className="mt-6 flex items-center gap-1 text-xs text-muted-foreground">
                            <ArrowsClockwise size={14} weight="duotone" /> Click to flip
                        </div>
                    </div>
                    {/* Back */}
                    <div
                        className="backface-hidden rotate-y-180 absolute inset-0 flex flex-col items-center justify-center border-2 border-primary bg-accent/20 p-8 text-center"
                    >
                        <div className="text-overline mb-3 text-primary">Answer</div>
                        <div className="font-display text-xl leading-snug tracking-tight">
                            {card.back}
                        </div>
                    </div>
                </motion.div>
            </div>

            <div className="flex items-center gap-3">
                <Button
                    variant="outline"
                    onClick={() => go(-1)}
                    data-testid="flashcard-prev-btn"
                >
                    <CaretLeft size={16} weight="bold" /> Prev
                </Button>
                <Button
                    variant="outline"
                    onClick={() => setFlipped(!flipped)}
                    data-testid="flashcard-flip-btn"
                >
                    <ArrowsClockwise size={16} weight="bold" className="mr-2" />
                    Flip
                </Button>
                <Button onClick={() => go(1)} data-testid="flashcard-next-btn">
                    Next <CaretRight size={16} weight="bold" />
                </Button>
            </div>
        </div>
    );
}
