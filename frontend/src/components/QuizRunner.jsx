import { useState } from "react";
import { lectureApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, ArrowClockwise } from "@phosphor-icons/react";
import { motion } from "framer-motion";
import { toast } from "sonner";

export default function QuizRunner({ lectureId, quiz = [] }) {
    const [answers, setAnswers] = useState(Array(quiz.length).fill(-1));
    const [result, setResult] = useState(null);
    const [submitting, setSubmitting] = useState(false);

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
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="border-2 border-primary bg-primary p-6 text-primary-foreground"
                    data-testid="quiz-result"
                >
                    <div className="text-overline text-accent">Result</div>
                    <div className="font-display text-5xl font-black tracking-tighter">
                        {result.score}/{result.total}
                    </div>
                    <div className="mt-1 text-base">
                        {result.percentage}% — {result.percentage >= 80 ? "Excellent" : result.percentage >= 60 ? "Solid pass" : "Time for revision"}
                    </div>
                    <Button
                        variant="secondary"
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
                    <div className="text-overline mb-2 text-primary">
                        Question {qi + 1}
                    </div>
                    <div className="font-display mb-4 text-xl font-bold tracking-tight">
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
                                    data-testid={`quiz-${qi}-option-${oi}`}
                                    onClick={() => pick(qi, oi)}
                                    className={`flex items-center gap-3 border px-4 py-3 text-left text-sm transition-all ${
                                        showCorrect
                                            ? "border-primary bg-primary text-primary-foreground"
                                            : wrongPick
                                                ? "border-destructive bg-destructive/10 text-foreground"
                                                : selected
                                                    ? "border-primary bg-accent/30"
                                                    : "border-border bg-card hover:border-primary/40"
                                    }`}
                                >
                                    <span className="flex h-6 w-6 shrink-0 items-center justify-center border border-current text-xs font-bold">
                                        {String.fromCharCode(65 + oi)}
                                    </span>
                                    <span className="flex-1">{opt}</span>
                                    {showCorrect && <CheckCircle size={18} weight="fill" />}
                                    {wrongPick && <XCircle size={18} weight="fill" />}
                                </button>
                            );
                        })}
                    </div>
                    {result && q.explanation && (
                        <div className="mt-3 border-l-2 border-accent bg-muted px-4 py-2 text-sm">
                            <span className="text-overline mr-2 text-primary">Why</span>
                            {q.explanation}
                        </div>
                    )}
                </div>
            ))}

            {!result && (
                <Button
                    size="lg"
                    onClick={submit}
                    disabled={submitting}
                    data-testid="quiz-submit-btn"
                    className="transition-transform hover:scale-[1.02] active:scale-[0.98]"
                >
                    {submitting ? "Grading…" : "Submit answers"}
                </Button>
            )}
        </div>
    );
}
