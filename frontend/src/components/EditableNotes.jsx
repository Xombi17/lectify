import { useEffect, useState } from "react";
import { Pencil, Check, X, Plus, TrashSimple } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { lectureApi } from "@/lib/api";
import { toast } from "sonner";

/**
 * Editable notes view for teachers.
 *  - Read mode (default + students): renders bullets, summary, concepts.
 *  - Edit mode (teacher only): inline textareas, add/remove rows.
 *
 * `onSaved(updated)` is called with the fresh lecture object after a save.
 */
export default function EditableNotes({ lecture, isOwner, onSaved, renderNoteExtras, renderConceptExtras }) {
    const m = lecture.materials || {};
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
    }, [lecture.id, lecture.updated_at]);

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
            <div data-testid="editable-notes-edit">
                <div className="mb-4 flex items-center justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={cancel} disabled={saving}>
                        <X size={14} className="mr-1" /> Cancel
                    </Button>
                    <Button size="sm" onClick={save} disabled={saving} data-testid="save-notes-btn">
                        <Check size={14} className="mr-1" />
                        {saving ? "Saving…" : "Save changes"}
                    </Button>
                </div>

                <div className="mb-6">
                    <div className="text-overline mb-2 text-primary">TL;DR</div>
                    <Textarea
                        value={summary}
                        onChange={(e) => setSummary(e.target.value)}
                        rows={3}
                        data-testid="edit-summary-textarea"
                    />
                </div>

                <div className="text-overline mb-3 text-muted-foreground">Smart notes</div>
                <div className="mb-2 space-y-2">
                    {notes.map((n, i) => (
                        <div key={i} className="flex gap-2">
                            <span className="font-mono mt-2 w-6 shrink-0 text-xs text-primary">
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
                                data-testid={`edit-note-${i}`}
                            />
                            <button
                                type="button"
                                onClick={() => setNotes(notes.filter((_, x) => x !== i))}
                                className="mt-1 h-9 w-9 text-muted-foreground hover:text-destructive"
                                title="Remove"
                            >
                                <TrashSimple size={14} weight="duotone" />
                            </button>
                        </div>
                    ))}
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setNotes([...notes, ""])}
                    className="mb-6"
                    data-testid="add-note-btn"
                >
                    <Plus size={14} className="mr-1" />
                    Add a note
                </Button>

                <div className="text-overline mb-3 text-muted-foreground">Key concepts</div>
                <div className="mb-2 flex flex-wrap gap-2">
                    {concepts.map((c, i) => (
                        <div key={i} className="flex items-center gap-1 border border-border bg-card">
                            <Input
                                value={c}
                                onChange={(e) => {
                                    const next = [...concepts];
                                    next[i] = e.target.value;
                                    setConcepts(next);
                                }}
                                className="h-8 w-44 border-0"
                                data-testid={`edit-concept-${i}`}
                            />
                            <button
                                type="button"
                                onClick={() =>
                                    setConcepts(concepts.filter((_, x) => x !== i))
                                }
                                className="h-8 w-8 text-muted-foreground hover:text-destructive"
                                title="Remove"
                            >
                                <X size={12} />
                            </button>
                        </div>
                    ))}
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setConcepts([...concepts, ""])}
                    data-testid="add-concept-btn"
                >
                    <Plus size={14} className="mr-1" />
                    Add a concept
                </Button>
            </div>
        );
    }

    // Read mode
    return (
        <div data-testid="editable-notes-read">
            {isOwner && (
                <div className="mb-4 flex justify-end">
                    <Button variant="outline" size="sm" onClick={startEdit} data-testid="edit-notes-btn">
                        <Pencil size={14} className="mr-1" />
                        Edit notes
                    </Button>
                </div>
            )}

            {m.summary && (
                <div className="mb-6 border-l-2 border-accent bg-card p-5">
                    <div className="text-overline mb-2 text-primary">TL;DR</div>
                    <p className="text-base leading-relaxed">{m.summary}</p>
                </div>
            )}

            <h3 className="text-overline mb-4 text-muted-foreground">Smart notes</h3>
            <ul className="space-y-3">
                {(m.smart_notes || []).map((n, i) => (
                    <li
                        key={i}
                        className="flex gap-3 border-b border-border pb-3 text-base leading-relaxed"
                    >
                        <span className="font-mono mt-1 text-xs text-primary">
                            {String(i + 1).padStart(2, "0")}
                        </span>
                        <span className="flex-1">{n}</span>
                        {renderNoteExtras?.(i, n)}
                    </li>
                ))}
            </ul>

            {(m.key_concepts || []).length > 0 && (
                <div className="mt-8">
                    <h3 className="text-overline mb-3 text-muted-foreground">Key concepts</h3>
                    <div className="flex flex-wrap gap-2">
                        {m.key_concepts.map((c, i) => (
                            <span
                                key={i}
                                className="inline-flex items-center gap-1 border border-primary/20 bg-accent/20 px-3 py-1 text-sm font-medium"
                            >
                                {c}
                                {renderConceptExtras?.(i, c)}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
