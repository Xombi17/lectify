import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Trash } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { bookmarkApi } from "@/lib/api";
import { toast } from "sonner";

const KIND_META = {
    concept: { label: "Concept" },
    note: { label: "Note" },
    flashcard: { label: "Flashcard" },
};

export default function BookmarksPage() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const reduce = useReducedMotion();

    const load = () => {
        setLoading(true);
        bookmarkApi
            .mine()
            .then(setItems)
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        load();
    }, []);

    const remove = async (id) => {
        try {
            await bookmarkApi.remove(id);
            setItems((prev) => prev.filter((b) => b.id !== id));
            toast.success("Bookmark removed");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Couldn't remove bookmark");
        }
    };

    // Group by lecture
    const grouped = items.reduce((acc, bm) => {
        (acc[bm.lecture_id] ||= { meta: bm, items: [] }).items.push(bm);
        return acc;
    }, {});

    return (
        <>
            <header className="head">
                <div>
                    <h1 className="text-display">Bookmarks</h1>
                    <p className="lede mt-3">Notes, concepts and flashcards you saved, grouped by lecture.</p>
                </div>
            </header>

            <div data-testid="bookmarks-list">
                {loading ? (
                    <div aria-busy="true" aria-label="Loading" className="grid gap-4">
                        <span className="sk" />
                        <span className="sk" />
                        <span className="sk" />
                    </div>
                ) : items.length === 0 ? (
                    <div className="empty">
                        <h2 className="text-2xl font-bold">A blank page</h2>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Tap the ribbon on a lecture to keep it here.
                        </p>
                        <span className="hand">nothing marked yet</span>
                    </div>
                ) : (
                    <div className="grid items-start gap-6 lg:grid-cols-2">
                        {Object.values(grouped).map(({ meta, items: lectureItems }) => (
                            <motion.section
                                key={meta.lecture_id}
                                className="slip slip--plain"
                                initial={reduce ? false : { opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                data-testid={`bookmark-group-${meta.lecture_id}`}
                            >
                                <div className="mb-3 grid gap-1">
                                    <h2 className="min-w-0 text-xl">
                                        <Link
                                            href={`/student/lectures/${meta.lecture_id}`}
                                            className="hover:underline"
                                        >
                                            {meta.lecture_title}
                                        </Link>
                                    </h2>
                                    <span className="text-sm text-muted-foreground">
                                        {meta.lecture_subject ? `${meta.lecture_subject} · ` : ""}
                                        {lectureItems.length} saved
                                    </span>
                                </div>
                                <div className="grid gap-2">
                                    {lectureItems.map((bm) => {
                                        const M = KIND_META[bm.kind] || KIND_META.note;
                                        return (
                                            <div
                                                key={bm.id}
                                                className="flex items-start gap-3 border-t border-border py-3"
                                            >
                                                <div className="min-w-0 flex-1">
                                                    <div className="text-overline text-muted-foreground">
                                                        {M.label}
                                                    </div>
                                                    <div className="mt-0.5 text-base">{bm.text}</div>
                                                </div>
                                                <Button
                                                    type="button"
                                                    variant="quiet"
                                                    size="icon"
                                                    onClick={() => remove(bm.id)}
                                                    aria-label="Remove bookmark"
                                                    className="shrink-0 hover:text-destructive"
                                                    data-testid={`remove-bookmark-${bm.id}`}
                                                >
                                                    <Trash size={16} weight="bold" />
                                                </Button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </motion.section>
                        ))}
                    </div>
                )}
            </div>
        </>
    );
}
