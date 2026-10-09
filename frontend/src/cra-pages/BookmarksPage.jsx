"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { BookmarkSimple, Cards, Note, Sparkle, Tag, Trash } from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
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
        bookmarkApi.mine().then(setItems).finally(() => setLoading(false));
    };

    useEffect(() => { load(); }, []);

    const remove = async (id) => {
        try {
            await bookmarkApi.remove(id);
            setItems((current) => current.filter((item) => item.id !== id));
            toast.success("Bookmark removed");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Couldn't remove bookmark");
        }
    };

    const grouped = items.reduce((groups, bookmark) => {
        (groups[bookmark.lecture_id] ||= { meta: bookmark, items: [] }).items.push(bookmark);
        return groups;
    }, {});

    return (
        <div className="animate-in">
            <section className="page-intro"><div><div className="eyebrow text-accent">Saved for later</div><h1>Your bookmarks.</h1><p>Concepts, notes, and flashcards you marked while studying.</p></div><span className="font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">{items.length} saved</span></section>
            <div data-testid="bookmarks-list">
                {loading ? <div className="space-y-px border border-border bg-border">{[1, 2, 3].map((item) => <div key={item} className="h-24 animate-pulse bg-card" />)}</div> : items.length === 0 ? <div className="empty-panel"><BookmarkSimple size={30} className="mx-auto text-accent" weight="duotone" /><h3 className="mt-4 text-2xl font-extrabold tracking-[-0.05em]">Nothing saved yet</h3><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">Open a lecture and save a concept, note, or flashcard when you want a quick route back.</p></div> : <div className="space-y-10">{Object.values(grouped).map(({ meta, items: lectureItems }) => <motion.section key={meta.lecture_id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} data-testid={`bookmark-group-${meta.lecture_id}`}><div className="mb-3 flex flex-wrap items-baseline justify-between gap-3 border-b border-border pb-3"><Link href={`/student/lectures/${meta.lecture_id}`} className="font-display text-lg font-extrabold tracking-[-0.04em] underline decoration-accent underline-offset-4 hover:text-accent">{meta.lecture_title}</Link><div className="flex items-center gap-2">{meta.lecture_subject && <Badge variant="outline">{meta.lecture_subject}</Badge>}<span className="font-mono text-[0.62rem] uppercase tracking-[0.1em] text-muted-foreground">{lectureItems.length} saved</span></div></div><div className="overflow-hidden border border-border">{lectureItems.map((bookmark) => { const kind = KIND_META[bookmark.kind] || KIND_META.note; const Icon = kind.icon; return <div key={bookmark.id} className="data-row group flex items-start gap-3 px-4 py-4 sm:px-5"><Icon size={18} weight="bold" className="mt-0.5 shrink-0 text-accent" /><div className="min-w-0 flex-1"><div className="eyebrow text-muted-foreground">{kind.label}</div><div className="mt-1 text-sm leading-7">{bookmark.text}</div></div><button type="button" onClick={() => remove(bookmark.id)} title="Remove bookmark" aria-label={`Remove ${kind.label.toLowerCase()} bookmark`} data-testid={`remove-bookmark-${bookmark.id}`} className="shrink-0 p-1 text-muted-foreground opacity-60 transition hover:text-destructive sm:opacity-0 sm:group-hover:opacity-100"><Trash size={16} weight="bold" /></button></div>; })}</div></motion.section>)}</div>}
            </div>
        </div>
    );
}
