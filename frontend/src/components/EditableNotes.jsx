import { useEffect, useState } from "react";
import {
    Pencil,
    Check,
    X,
    Plus,
    TrashSimple,
    Sparkle,
    BookBookmark,
    GraduationCap,
    CheckCircle,
    Brain,
    ChatCircle,
    ArrowRight,
} from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { lectureApi } from "@/lib/api";
import { toast } from "sonner";

/**
 * Editable notes view for lectures.
 *  - Read mode: 2-column responsive layout with rich TL;DR, numbered smart notes,
 *    and a sticky study companion sidebar on desktop (stacks on mobile).
 *  - Edit mode (teacher only): inline textareas, add/remove rows.
 *
 * `onSaved(updated)` is called with the fresh lecture object after a save.
 */
export default function EditableNotes({
    lecture,
    materials,
    isOwner,
    onSaved,
    renderNoteExtras,
    renderConceptExtras,
    onTabChange,
    quizCount = 0,
    flashcardsCount = 0,
    hasTranscript = false,
}) {
    const m = materials || lecture?.materials || {};
    const [editing, setEditing] = useState(false);
    const [summary, setSummary] = useState(m.summary || "");
    const [notes, setNotes] = useState(m.smart_notes || []);
    const [concepts, setConcepts] = useState(m.key_concepts || []);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!editing) {
            setSummary(m.summary || "");
            setNotes(m.smart_notes || []);
            setConcepts(m.key_concepts || []);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [lecture?.id, lecture?.updated_at, materials]);

    const startEdit = () => {
        setSummary(m.summary || "");
        setNotes([...(m.smart_notes || [])]);
        setConcepts([...(m.key_concepts || [])]);
        setEditing(true);
    };

    const cancel = () => setEditing(false);

    const save = async () => {
        setSaving(true);
        try {
            const updated = await lectureApi.editMaterials(lecture.id, {
                summary,
                smart_notes: notes,
                key_concepts: concepts,
            });
            toast.success("Notes saved");
            setEditing(false);
            onSaved?.(updated);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Couldn't save notes");
        } finally {
            setSaving(false);
        }
    };

    if (editing) {
        return (
            <div data-testid="editable-notes-edit" className="max-w-4xl space-y-6">
                <div className="flex items-center justify-between border-b border-border pb-3">
                    <span className="font-sans text-sm font-medium text-foreground">Editing Lecture Notes</span>
                    <div className="flex items-center gap-2">
                        <Button variant="ghost" size="sm" onClick={cancel} disabled={saving}>
                            <X size={14} className="mr-1" /> Cancel
                        </Button>
                        <Button size="sm" variant="pen" onClick={save} disabled={saving} data-testid="save-notes-btn">
                            <Check size={14} className="mr-1" />
                            {saving ? "Saving…" : "Save changes"}
                        </Button>
                    </div>
                </div>

                <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
                    <div className="text-overline mb-2 text-primary">TL;DR / Summary</div>
                    <Textarea
                        value={summary}
                        onChange={(e) => setSummary(e.target.value)}
                        rows={3}
                        data-testid="edit-summary-textarea"
                        className="font-serif text-base"
                    />
                </div>

                <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="text-overline text-muted-foreground">Smart notes</div>
                        <Button
                            variant="default"
                            size="sm"
                            onClick={() => setNotes([...notes, ""])}
                            data-testid="add-note-btn"
                        >
                            <Plus size={14} className="mr-1" />
                            Add note
                        </Button>
                    </div>
                    <div className="space-y-3">
                        {notes.map((n, i) => (
                            <div key={i} className="flex gap-2.5 items-start">
                                <span className="font-mono mt-2 flex h-6 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-sm font-medium text-primary">
                                    {String(i + 1).padStart(2, "0")}
                                </span>
                                <Textarea
                                    value={n}
                                    onChange={(e) => {
                                        const next = [...notes];
                                        next[i] = e.target.value;
                                        setNotes(next);
                                    }}
                                    rows={2}
                                    className="font-serif text-base flex-1"
                                    data-testid={`edit-note-${i}`}
                                />
                                <button
                                    type="button"
                                    onClick={() => setNotes(notes.filter((_, x) => x !== i))}
                                    className="mt-1 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                                    title="Remove note"
                                >
                                    <TrashSimple size={14} weight="regular" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="text-overline text-muted-foreground">Key concepts</div>
                        <Button
                            variant="default"
                            size="sm"
                            onClick={() => setConcepts([...concepts, ""])}
                            data-testid="add-concept-btn"
                        >
                            <Plus size={14} className="mr-1" />
                            Add concept
                        </Button>
                    </div>
                    <div className="flex flex-wrap gap-2.5">
                        {concepts.map((c, i) => (
                            <div key={i} className="flex items-center gap-1 rounded-full border border-border bg-background pl-3 pr-1 py-0.5">
                                <Input
                                    value={c}
                                    onChange={(e) => {
                                        const next = [...concepts];
                                        next[i] = e.target.value;
                                        setConcepts(next);
                                    }}
                                    className="w-40 border-0 h-8 px-1 text-sm bg-transparent focus-visible:ring-0"
                                    data-testid={`edit-concept-${i}`}
                                />
                                <button
                                    type="button"
                                    onClick={() =>
                                        setConcepts(concepts.filter((_, x) => x !== i))
                                    }
                                    className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
                                    title="Remove concept"
                                >
                                    <X size={12} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    const noteCount = (m.smart_notes || []).length;
    const conceptCount = (m.key_concepts || []).length;
    const estReadTime = Math.max(
        1,
        Math.round(((m.smart_notes || []).join(" ").split(/\s+/).length + (m.summary || "").split(/\s+/).length) / 160)
    );

    // Read mode
    return (
        <div data-testid="editable-notes-read" className="notes w-full">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:gap-10 items-start">
                {/* Main reading column */}
                <div className="min-w-0 lg:col-span-8 space-y-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm font-sans text-muted-foreground">
                            <span>~{estReadTime} min read</span>
                            <span>•</span>
                            <span>{noteCount} takeaways</span>
                        </div>
                        {isOwner && (
                            <Button variant="default" size="sm" onClick={startEdit} data-testid="edit-notes-btn">
                                <Pencil size={14} className="mr-1.5" />
                                Edit notes
                            </Button>
                        )}
                    </div>

                    {m.summary && (
                        <div className="relative rounded-xl border border-primary/20 bg-card p-5 sm:p-6 shadow-sm ring-1 ring-primary/5 transition-all">
                            <div className="mb-3 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary">
                                        <Sparkle size={14} weight="bold" />
                                    </span>
                                    <span className="text-overline text-primary">TL;DR • Executive Summary</span>
                                </div>
                            </div>
                            <p className="text-base sm:text-lg leading-relaxed text-foreground/90 font-serif">
                                {m.summary}
                            </p>
                        </div>
                    )}

                    <div className="space-y-4 pt-2">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <h3 className="text-overline text-muted-foreground">
                                    Smart notes
                                </h3>
                                <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-sm text-muted-foreground">
                                    {noteCount}
                                </span>
                            </div>
                        </div>

                        <ul className="!pl-0 space-y-3 list-none">
                            {(m.smart_notes || []).map((n, i) => (
                                <li
                                    key={i}
                                    id={`note-${i}`}
                                    tabIndex={-1}
                                    className="group relative flex items-start gap-3.5 rounded-xl border border-border/70 bg-card/60 p-4 transition-all duration-150 hover:border-border hover:bg-card"
                                >
                                    <span className="font-mono mt-0.5 flex h-6 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-sm font-medium text-primary">
                                        {String(i + 1).padStart(2, "0")}
                                    </span>
                                    <span className="flex-1 text-base leading-relaxed text-foreground/90 font-serif">
                                        {n}
                                    </span>
                                    {renderNoteExtras && (
                                        <div className="shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
                                            {renderNoteExtras(i, n)}
                                        </div>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Mobile-only Key Concepts (shown below notes on smaller viewports) */}
                    {conceptCount > 0 && (
                        <div id="key-concepts-mobile" tabIndex={-1} className="block lg:hidden mt-8 rounded-xl border border-border/70 bg-card p-5">
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="text-overline text-muted-foreground">Key concepts</h3>
                                <span className="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-sm text-primary">{conceptCount}</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {m.key_concepts.map((c, i) => (
                                    <span
                                        key={i}
                                        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 font-sans text-sm font-medium text-foreground"
                                    >
                                        <span>{c}</span>
                                        {renderConceptExtras?.(i, c)}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Right Companion Sidebar (sticky on desktop) */}
                <div className="hidden lg:block lg:col-span-4 space-y-5 lg:sticky lg:top-8">
                    {/* Key Concepts Card */}
                    {conceptCount > 0 && (
                        <div id="key-concepts" tabIndex={-1} className="rounded-xl border border-border/70 bg-card p-5 shadow-sm">
                            <div className="flex items-center justify-between mb-3.5">
                                <div className="flex items-center gap-2">
                                    <BookBookmark size={16} className="text-primary" />
                                    <h3 className="font-sans text-sm font-medium uppercase tracking-wider text-foreground">
                                        Key Concepts
                                    </h3>
                                </div>
                                <span className="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-sm font-medium text-primary">
                                    {conceptCount}
                                </span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {m.key_concepts.map((c, i) => (
                                    <span
                                        key={i}
                                        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/80 py-1 pl-3.5 pr-2 font-sans text-sm font-medium text-foreground transition-all hover:border-primary/50 hover:bg-muted"
                                    >
                                        <span>{c}</span>
                                        {renderConceptExtras?.(i, c)}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Interactive Study Companion Card */}
                    <div className="rounded-xl border border-border/70 bg-card p-5 shadow-sm space-y-4">
                        <div className="flex items-center gap-2">
                            <GraduationCap size={18} className="text-primary" />
                            <h3 className="font-sans text-sm font-medium uppercase tracking-wider text-foreground">
                                Study Companion
                            </h3>
                        </div>
                        <p className="font-sans text-sm text-muted-foreground leading-relaxed">
                            Test your retention and practice active recall from this lecture.
                        </p>

                        <div className="space-y-2.5 pt-1">
                            {quizCount > 0 && (
                                <button
                                    type="button"
                                    onClick={() => onTabChange?.("quiz")}
                                    className="group flex w-full items-center justify-between rounded-xl border border-border/80 bg-background/60 p-3 text-left transition-all hover:border-primary/50 hover:bg-muted/80"
                                >
                                    <div className="flex items-center gap-3">
                                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                            <CheckCircle size={16} />
                                        </span>
                                        <div>
                                            <div className="font-sans text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                                Take Practice Quiz
                                            </div>
                                            <div className="font-sans text-sm text-muted-foreground">
                                                {quizCount} questions generated
                                            </div>
                                        </div>
                                    </div>
                                    <ArrowRight size={14} className="text-muted-foreground group-hover:translate-x-0.5 group-hover:text-primary transition-all" />
                                </button>
                            )}

                            {flashcardsCount > 0 && (
                                <button
                                    type="button"
                                    onClick={() => onTabChange?.("flashcards")}
                                    className="group flex w-full items-center justify-between rounded-xl border border-border/80 bg-background/60 p-3 text-left transition-all hover:border-primary/50 hover:bg-muted/80"
                                >
                                    <div className="flex items-center gap-3">
                                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                            <Brain size={16} />
                                        </span>
                                        <div>
                                            <div className="font-sans text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                                Spaced Flashcards
                                            </div>
                                            <div className="font-sans text-sm text-muted-foreground">
                                                {flashcardsCount} cards with SM-2 review
                                            </div>
                                        </div>
                                    </div>
                                    <ArrowRight size={14} className="text-muted-foreground group-hover:translate-x-0.5 group-hover:text-primary transition-all" />
                                </button>
                            )}

                            {hasTranscript && (
                                <button
                                    type="button"
                                    onClick={() => onTabChange?.("chat")}
                                    className="group flex w-full items-center justify-between rounded-xl border border-border/80 bg-background/60 p-3 text-left transition-all hover:border-primary/50 hover:bg-muted/80"
                                >
                                    <div className="flex items-center gap-3">
                                        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                                            <ChatCircle size={16} />
                                        </span>
                                        <div>
                                            <div className="font-sans text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                                                Ask Doubt AI
                                            </div>
                                            <div className="font-sans text-sm text-muted-foreground">
                                                Transcript-grounded tutor
                                            </div>
                                        </div>
                                    </div>
                                    <ArrowRight size={14} className="text-muted-foreground group-hover:translate-x-0.5 group-hover:text-primary transition-all" />
                                </button>
                            )}
                        </div>
                    </div>

                    {/* Lecture Insights summary */}
                    <div className="rounded-xl border border-border/70 bg-card p-4 shadow-sm">
                        <div className="grid grid-cols-2 gap-3 text-center font-sans">
                            <div className="rounded-lg bg-background/60 border border-border/40 p-2.5">
                                <div className="font-mono text-base font-bold text-foreground">
                                    {noteCount}
                                </div>
                                <div className="text-sm text-muted-foreground mt-0.5">Key Points</div>
                            </div>
                            <div className="rounded-lg bg-background/60 border border-border/40 p-2.5">
                                <div className="font-mono text-base font-bold text-foreground">
                                    {conceptCount}
                                </div>
                                <div className="text-sm text-muted-foreground mt-0.5">Key Concepts</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
