import { useEffect, useState } from "react";
import { BookmarkSimple } from "@phosphor-icons/react";
import { bookmarkApi } from "@/lib/api";
import { toast } from "sonner";

/**
 * Inline bookmark button. Optimistic create; on mount fetches existing state
 * from a parent-supplied cache to avoid N round-trips per page.
 */
export default function BookmarkButton({
    lectureId,
    kind,
    text,
    refIndex = null,
    existing = null,
    onToggle,
    size = 16,
}) {
    const [busy, setBusy] = useState(false);
    const [bookmark, setBookmark] = useState(existing);

    useEffect(() => {
        setBookmark(existing);
    }, [existing]);

    const toggle = async (e) => {
        e?.stopPropagation();
        if (busy) return;
        setBusy(true);
        try {
            if (bookmark) {
                await bookmarkApi.remove(bookmark.id);
                setBookmark(null);
                onToggle?.(null);
                toast.success("Bookmark removed");
            } else {
                const bm = await bookmarkApi.create({
                    lecture_id: lectureId,
                    kind,
                    text,
                    ref_index: refIndex,
                });
                setBookmark(bm);
                onToggle?.(bm);
                toast.success("Bookmarked");
            }
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Couldn't save bookmark");
        } finally {
            setBusy(false);
        }
    };

    return (
        <button
            type="button"
            onClick={toggle}
            disabled={busy}
            aria-pressed={!!bookmark}
            data-testid={`bookmark-${kind}-${refIndex ?? "none"}`}
            className={`inline-flex h-7 w-7 items-center justify-center transition-colors ${
                bookmark
                    ? "text-primary"
                    : "text-muted-foreground hover:text-primary"
            }`}
            title={bookmark ? "Remove bookmark" : "Bookmark"}
        >
            <BookmarkSimple
                size={size}
                weight={bookmark ? "fill" : "duotone"}
            />
        </button>
    );
}
