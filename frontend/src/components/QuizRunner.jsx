import { useState } from "react";
import { lectureApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Check, X, ArrowClockwise } from "@/components/icons";
import { motion, useReducedMotion } from "framer-motion";
import { toast } from "sonner";

export default function QuizRunner({ lectureId, quiz = [] }) {
    const [answers, setAnswers] = useState(Array(quiz.length).fill(-1));
    const [result, setResult] = useState(null);
    const [submitting, setSubmitting] = useState(false);
    const reduce = useReducedMotion();

    if (!quiz.length) {
        return <div className="text-sm text-muted-foreground">No quiz generated yet.</div>;
    }

    const pick = (qi, oi) => {
        if (result) return;
        const next = [...answers];
        next[qi] = oi;
        setAnswers(next);
    };

    const submit = async () => {
        if (answers.some((a) => a < 0)) {
            return toast.error("Answer every question before submitting");
        }
        setSubmitting(true);
        try {
            const r = await lectureApi.submitQuiz(lectureId, answers);
            setResult(r);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Failed to grade quiz");
        } finally {
            setSubmitting(false);
        }
    };

    const reset = () => {
        setAnswers(Array(quiz.length).fill(-1));
        setResult(null);
    };

    return (
        <div className="space-y-8">
            {result && (
                <motion.div
                    initial={{ opacity: 0, y: reduce ? 0 : -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="rounded-[var(--radius)] border border-border bg-card p-6"
                    data-testid="quiz-result"
                >
                    <div className="text-overline text-primary">Result</div>
                    <div className="text-section tabular-nums" data-testid="quiz-score">
                        {result.score}/{result.total}
                    </div>
                    <div className="mt-1 text-base">
                        {result.percentage}% — {result.percentage >= 80 ? "Excellent" : result.percentage >= 60 ? "Solid pass" : "Time for revision"}
                    </div>
                    <Button
                        variant="default"
                        onClick={reset}
                        className="mt-4"
                        data-testid="quiz-retry-btn"
                    >
                        <ArrowClockwise size={16} weight="bold" className="mr-2" />
                        Try again
                    </Button>
                </motion.div>
            )}

            {quiz.map((q, qi) => (
                <div key={qi} data-testid={`quiz-question-${qi}`}>
                    <div className="mb-2 font-mono text-sm text-primary">
                        Question {qi + 1}
                    </div>
                    <div className="mb-4 font-display text-2xl">
                        {q.question}
                    </div>
                    <div className="grid gap-2">
                        {q.options.map((opt, oi) => {
                            const selected = answers[qi] === oi;
                            const correct = result?.correct_answers[qi] === oi;
                            const wrongPick = result && selected && !correct;
                            const showCorrect = result && correct;
                            return (
                                <button
                                    key={oi}
                                    type="button"
                                    aria-pressed={selected}
                                    data-testid={`quiz-${qi}-option-${oi}`}
                                    onClick={() => pick(qi, oi)}
                                    className={`flex min-h-11 w-full items-center gap-3 rounded-[var(--r)] border px-4 py-3 text-left text-base ${
                                        showCorrect
                                            ? "border-primary bg-card text-primary"
                                            : wrongPick
                                                ? "border-destructive bg-card text-destructive"
                                                : selected
                                                    ? "border-primary bg-accent text-accent-foreground"
                                                    : "border-border bg-card hover:border-primary/40"
                                    }`}
                                >
                                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-current font-mono text-sm">
                                        {String.fromCharCode(65 + oi)}
                                    </span>
                                    <span className="flex-1">{opt}</span>
                                    {showCorrect && (
                                        <span className="inline-flex items-center gap-1 text-sm font-bold">
                                            <Check size={18} weight="bold" aria-hidden="true" />
                                            Correct
                                        </span>
                                    )}
                                    {wrongPick && (
                                        <span className="inline-flex items-center gap-1 text-sm font-bold">
                                            <X size={18} weight="bold" aria-hidden="true" />
                                            Wrong
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                    {result && q.explanation && (
                        <div className="mt-3 rounded-[var(--r)] bg-muted px-4 py-3 text-sm">
                            <span className="text-overline mr-2 text-primary">Why</span>
                            {q.explanation}
                        </div>
                    )}
                </div>
            ))}

            {!result && (
                <Button
                    size="lg"
                    variant="pen"
                    onClick={submit}
                    disabled={submitting}
                    data-testid="quiz-submit-btn"
                    className="motion-safe:transition-transform motion-safe:hover:scale-[1.02]"
                >
                    {submitting ? "Grading…" : "Submit answers"}
                </Button>
            )}
        </div>
    );
}
