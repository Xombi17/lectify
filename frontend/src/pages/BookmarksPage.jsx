import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
    BookmarkSimple,
    Sparkle,
    Note,
    Cards,
    Tag,
    Trash,
} from "@phosphor-icons/react";
import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { bookmarkApi } from "@/lib/api";
import { toast } from "sonner";

const KIND_META = {
    concept: { icon: Tag, label: "Concept" },
    note: { icon: Note, label: "Note" },
    flashcard: { icon: Cards, label: "Flashcard" },
};

export default function BookmarksPage() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);

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
        <AppShell>
            <div className="text-overline mb-3 text-primary">Saved for later</div>
            <h1 className="font-display text-4xl font-black tracking-tighter sm:text-5xl">
                Your bookmarks.
            </h1>
            <p className="mt-3 max-w-xl text-base text-muted-foreground">
                Concepts, notes, and flashcards you starred across all lectures.
            </p>

            <div className="mt-10" data-testid="bookmarks-list">
                {loading ? (
                    <div className="grid gap-3">
                        {[1, 2, 3].map((n) => (
                            <div key={n} className="h-24 animate-pulse border border-border bg-muted/40" />
                        ))}
                    </div>
                ) : items.length === 0 ? (
                    <div className="border-2 border-dashed border-border bg-card p-10 text-center">
                        <BookmarkSimple
                            size={32}
                            weight="duotone"
                            className="mx-auto text-muted-foreground"
                        />
                        <h3 className="font-display mt-3 text-2xl font-bold tracking-tight">
                            No bookmarks yet
                        </h3>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Open a lecture and tap the bookmark icon next to any concept, note, or
                            flashcard.
                        </p>
                    </div>
                ) : (
                    <div className="space-y-8">
                        {Object.values(grouped).map(({ meta, items: lectureItems }) => (
                            <motion.section
                                key={meta.lecture_id}
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                data-testid={`bookmark-group-${meta.lecture_id}`}
                            >
                                <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2 border-b border-border pb-2">
                                    <Link
                                        to={`/student/lectures/${meta.lecture_id}`}
                                        className="font-display text-lg font-bold tracking-tight text-primary underline-offset-4 hover:underline"
                                    >
                                        {meta.lecture_title}
                                    </Link>
                                    <div className="flex items-center gap-2">
                                        {meta.lecture_subject && (
                                            <Badge variant="outline">{meta.lecture_subject}</Badge>
                                        )}
                                        <span className="text-overline text-muted-foreground">
                                            {lectureItems.length} saved
                                        </span>
                                    </div>
                                </div>
                                <div className="grid gap-2">
                                    {lectureItems.map((bm) => {
                                        const M = KIND_META[bm.kind] || KIND_META.note;
                                        const Icon = M.icon;
                                        return (
                                            <div
                                                key={bm.id}
                                                className="group flex items-start gap-3 border border-border bg-card px-4 py-3 transition-all hover:border-primary/40"
                                            >
                                                <Icon
                                                    size={18}
                                                    weight="duotone"
                                                    className="mt-1 shrink-0 text-primary"
                                                />
                                                <div className="min-w-0 flex-1">
                                                    <div className="text-overline text-muted-foreground">
                                                        {M.label}
                                                    </div>
                                                    <div className="mt-0.5 text-sm leading-relaxed">
                                                        {bm.text}
                                                    </div>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => remove(bm.id)}
                                                    className="opacity-0 transition-opacity group-hover:opacity-100"
                                                    title="Remove"
                                                    data-testid={`remove-bookmark-${bm.id}`}
                                                >
                                                    <Trash size={16} weight="duotone" className="text-destructive" />
                                                </button>
                                            </div>
                                        );
                                    })}
                                </div>
                            </motion.section>
                        ))}
                    </div>
                )}
            </div>
        </AppShell>
    );
}
