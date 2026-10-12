"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { lectureApi, API, bookmarkApi } from "@/lib/api";
import { STATUS_LABEL, statusPillKind } from "@/lib/lectureStatus";
import { formatProcessing } from "@/lib/formatDuration";
import { useAuth } from "@/lib/auth";
import FlashcardDeck from "@/components/FlashcardDeck";
import QuizRunner from "@/components/QuizRunner";
import DoubtChat from "@/components/DoubtChat";
import EditableNotes from "@/components/EditableNotes";
import BookmarkButton from "@/components/BookmarkButton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Lightning,
    CheckCircle,
    WarningCircle,
    PaperPlaneTilt,
    Trash,
    EyeSlash,
    Translate,
    DownloadSimple,
} from "@phosphor-icons/react";
import { toast } from "sonner";

const STATUS_LABEL_FALLBACK = {
    uploaded: "Queued",
    processing: "AI is processing",
    ready: "Ready",
    error: "Error",
};

export default function LectureDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { user } = useAuth();
    const [lecture, setLecture] = useState(null);
    const [audioToken, setAudioToken] = useState(null);
    const [downloadingPdf, setDownloadingPdf] = useState(false);

    const downloadPdf = async () => {
        if (!lecture?.id || downloadingPdf) return;
        setDownloadingPdf(true);
        try {
            const token = localStorage.getItem("lm_token");
            const r = await fetch(lectureApi.pdfUrl(lecture.id), {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            if (!r.ok) throw new Error(`PDF export failed: ${r.status}`);
            const blob = await r.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${(lecture.title || "lecture").slice(0, 60)} - Notes.pdf`.replace(/[^\w\-. ]+/g, "-");
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        } catch {
            toast.error("Couldn't download PDF");
        } finally {
            setDownloadingPdf(false);
        }
    };

    useEffect(() => {
        let cancelled = false;
        let timer;
        const load = async () => {
            try {
                const data = await lectureApi.get(id);
                if (cancelled) return;
                setLecture(data);
                if (["processing", "uploaded", "uploading", "queued", "retrying"].includes(data.status)) {
                    timer = setTimeout(load, 4000);
                }
            } catch (err) {
                toast.error(err?.response?.data?.detail || "Failed to load lecture");
                router.back();
            }
        };
        load();
        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
    }, [id, router]);

    // Prefer presigned audio-url (no auth header); fall back to authed blob stream.
    useEffect(() => {
        if (!lecture?.id) return;
        let cancelled = false;
        let blobUrl = null;
        const load = async () => {
            try {
                const data = await lectureApi.audioPresignedUrl(lecture.id);
                if (!cancelled && data?.url) {
                    setAudioToken(data.url);
                    return;
                }
            } catch {
                // fall through to blob on 501/403/404
            }
            try {
                const token = localStorage.getItem("lm_token");
                const r = await fetch(`${API}/lectures/${lecture.id}/audio`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!r.ok) throw r;
                const blob = await r.blob();
                blobUrl = URL.createObjectURL(blob);
                if (!cancelled) setAudioToken(blobUrl);
            } catch {
                if (!cancelled) setAudioToken(null);
            }
        };
        load();
        return () => {
            cancelled = true;
            if (blobUrl) URL.revokeObjectURL(blobUrl);
        };
    }, [lecture?.id]);

    if (!lecture) {
        return (
            <div className="h-40 animate-pulse border border-border bg-muted/40" />
        );
    }

    const isOwner = user?.role === "teacher" && user.id === lecture.teacher_id;
    const ready = lecture.status === "ready";
    const pillKind = statusPillKind(lecture.status);
    const pillLabel = STATUS_LABEL[lecture.status] ?? STATUS_LABEL_FALLBACK[lecture.status] ?? lecture.status;

    const togglePublish = async () => {
        try {
            const updated = lecture.published
                ? await lectureApi.unpublish(lecture.id)
                : await lectureApi.publish(lecture.id);
            setLecture(updated);
            toast.success(updated.published ? "Published to students" : "Unpublished");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Action failed");
        }
    };

    const remove = async () => {
        if (!confirm("Delete this lecture? This cannot be undone.")) return;
        try {
            await lectureApi.remove(lecture.id);
            toast.success("Lecture deleted");
            router.push("/teacher/dashboard");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Delete failed");
        }
    };

    return (
    <>
            <div className="mb-8">
                <div className="text-overline mb-2 text-primary">Lecture</div>
                <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-end">
                    <div>
                        <h1 className="font-display text-3xl font-black tracking-tighter sm:text-4xl">
                            {lecture.title}
                        </h1>
                        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                            {lecture.subject && <Badge variant="outline">{lecture.subject}</Badge>}
                            {lecture.semester && <Badge variant="outline">{lecture.semester}</Badge>}
                            <Badge
                                data-testid="status-badge"
                                data-kind={pillKind}
                                className={
                                    pillKind === "ready"
                                        ? "bg-primary text-primary-foreground"
                                        : pillKind === "failed"
                                            ? "bg-destructive text-destructive-foreground"
                                            : "bg-accent/30 text-accent-foreground"
                                }
                            >
                                {pillKind === "ready" ? (
                                    <CheckCircle size={14} weight="duotone" className="mr-1" />
                                ) : pillKind === "failed" ? (
                                    <WarningCircle size={14} weight="duotone" className="mr-1" />
                                ) : (
                                    <Lightning size={14} weight="duotone" className="mr-1" />
                                )}
                                {pillLabel}
                            </Badge>
                            {ready && formatProcessing(lecture.processing_seconds) && (
                                <span data-testid="processing-time" className="text-xs">
                                    Processed in {formatProcessing(lecture.processing_seconds)}
                                </span>
                            )}
                            {lecture.published && (
                                <Badge className="bg-accent text-accent-foreground">Published</Badge>
                            )}
                        </div>
                    </div>

                    {isOwner && (
                        <div className="flex gap-2">
                            {ready && (
                                <Button
                                    variant="outline"
                                    onClick={downloadPdf}
                                    disabled={downloadingPdf}
                                    data-testid="download-pdf-btn"
                                >
                                    <DownloadSimple size={16} weight="duotone" className="mr-2" />
                                    {downloadingPdf ? "Preparing…" : "PDF"}
                                </Button>
                            )}
                            <Button
                                onClick={togglePublish}
                                disabled={!ready}
                                data-testid="publish-toggle-btn"
                            >
                                {lecture.published ? (
                                    <>
                                        <EyeSlash size={16} weight="duotone" className="mr-2" />
                                        Unpublish
                                    </>
                                ) : (
                                    <>
                                        <PaperPlaneTilt size={16} weight="duotone" className="mr-2" />
                                        Publish to students
                                    </>
                                )}
                            </Button>
                            <Button
                                variant="ghost"
                                onClick={remove}
                                data-testid="delete-lecture-btn"
                            >
                                <Trash size={16} weight="duotone" />
                            </Button>
                        </div>
                    )}
                </div>
            </div>

            {audioToken && (
                <div className="mb-8 border border-border bg-card p-4">
                    <div className="text-overline mb-2 text-muted-foreground">Original recording</div>
                    <audio controls src={audioToken} className="w-full" data-testid="lecture-audio" />
                </div>
            )}

            {pillKind === "processing" ? (
                <ProcessingState lecture={lecture} />
            ) : pillKind === "failed" ? (
                <ErrorState message={lecture.error_message} deadLetter={lecture.status === "dead_letter"} />
            ) : (
                <ContentTabs lecture={lecture} isOwner={isOwner} onLectureUpdate={setLecture} />
            )}
    </>
    );
}

function ProcessingState({ lecture }) {
    const total = lecture.progress_total || 0;
    const step = lecture.progress_step || 0;
    const pct = total > 0 ? Math.min(100, Math.round((step / total) * 100)) : null;
    const label = lecture.progress_label || "Working on it…";
    const isLong = (lecture.duration_seconds || 0) > 30 * 60;

    return (
        <div className="border-2 border-dashed border-border bg-card p-12 text-center">
            <div className="mx-auto mb-5 flex h-16 w-16 animate-pulse items-center justify-center bg-accent">
                <Lightning size={32} weight="duotone" className="text-accent-foreground" />
            </div>
            <h3 className="font-display text-2xl font-black tracking-tighter">
                AI is digesting your lecture
            </h3>
            <p
                className="mt-2 text-sm text-muted-foreground"
                data-testid="processing-label"
            >
                {label}
            </p>

            {pct !== null && (
                <div className="mx-auto mt-6 max-w-md">
                    <div className="mb-2 flex items-center justify-between text-xs">
                        <span className="text-overline text-muted-foreground">Progress</span>
                        <span className="font-mono text-primary" data-testid="processing-percent">
                            {pct}%
                        </span>
                    </div>
                    <div className="h-2 w-full bg-muted">
                        <div
                            className="h-full bg-primary transition-all duration-500"
                            style={{ width: `${pct}%` }}
                            data-testid="processing-bar"
                        />
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                        Step {step} of {total}
                    </div>
                </div>
            )}

            {isLong && lecture.chunk_count > 0 && (
                <p className="mt-6 inline-flex items-center gap-2 border border-border bg-background px-3 py-1 text-xs text-muted-foreground">
                    <Lightning size={12} weight="duotone" />
                    Long lecture detected · split into{" "}
                    <span className="font-mono text-primary">{lecture.chunk_count}</span>{" "}
                    chunks for hierarchical processing
                </p>
            )}
        </div>
    );
}

function ErrorState({ message, deadLetter }) {
    return (
        <div className="border-2 border-destructive bg-destructive/10 p-8">
            <div className="flex items-center gap-3">
                <WarningCircle size={24} weight="duotone" className="text-destructive" />
                <h3 className="font-display text-2xl font-black tracking-tighter">
                    Processing failed
                </h3>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
                {message || "Processing failed — contact your teacher."}
            </p>
            {deadLetter && (
                <p className="mt-2 text-xs text-muted-foreground">
                    This lecture exhausted all retries. Contact your teacher to re-queue it.
                </p>
            )}
            <p className="mt-2 text-xs text-muted-foreground">
                Verify that <code className="font-mono">GEMINI_API_KEY</code> is set in
                <code className="font-mono"> backend/.env</code> and try uploading again.
            </p>
        </div>
    );
}

function ContentTabs({ lecture, isOwner, onLectureUpdate }) {
    const baseMaterials = lecture.materials || {};
    const [language, setLanguage] = useState("original");
    const [translating, setTranslating] = useState(false);
    const [translated, setTranslated] = useState(null);
    const m = translated || baseMaterials;
    const showOriginal = language === "original";

    // Bookmarks (only for the original-language view)
    const [bookmarks, setBookmarks] = useState([]);
    useEffect(() => {
        bookmarkApi
            .forLecture(lecture.id)
            .then(setBookmarks)
            .catch(() => setBookmarks([]));
    }, [lecture.id]);

    const findBookmark = (kind, refIndex) =>
        bookmarks.find(
            (b) => b.kind === kind && b.ref_index === refIndex
        ) || null;

    const onBookmarkToggle = (kind, refIndex, bm) => {
        setBookmarks((prev) => {
            const without = prev.filter(
                (b) => !(b.kind === kind && b.ref_index === refIndex)
            );
            return bm ? [...without, bm] : without;
        });
    };

    const onLanguage = async (lang) => {
        setLanguage(lang);
        if (lang === "original") {
            setTranslated(null);
            return;
        }
        setTranslating(true);
        try {
            const r = await lectureApi.translate(lecture.id, lang);
            setTranslated({
                summary: r.summary,
                smart_notes: r.smart_notes || [],
                key_concepts: r.key_concepts || [],
                flashcards: r.flashcards || baseMaterials.flashcards,
            });
            toast.success(`Notes translated to ${lang}`);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Translation failed");
            setLanguage("original");
        } finally {
            setTranslating(false);
        }
    };

    return (
        <Tabs defaultValue="notes" className="w-full" data-testid="lecture-tabs">
            <TabsList className="h-auto w-full justify-start gap-6 rounded-none border-b border-border bg-transparent p-0">
                {[
                    ["notes", "Smart Notes"],
                    ["quiz", "Quiz"],
                    ["flashcards", "Flashcards"],
                    ["chat", "Doubt Chat"],
                    ["transcript", "Transcript"],
                ].map(([v, label]) => (
                    <TabsTrigger
                        key={v}
                        value={v}
                        data-testid={`tab-${v}`}
                        className="rounded-none border-b-2 border-transparent bg-transparent px-1 pb-3 pt-0 font-display text-base font-bold tracking-tight text-muted-foreground shadow-none data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none"
                    >
                        {label}
                    </TabsTrigger>
                ))}
            </TabsList>

            <TabsContent value="notes" className="mt-8" data-testid="notes-tab-content">
                <div className="mb-6 flex flex-wrap items-center gap-3 border-b border-border pb-3">
                    <Translate size={16} weight="duotone" className="text-primary" />
                    <span className="text-overline text-muted-foreground">View in</span>
                    <Select value={language} onValueChange={onLanguage} disabled={translating}>
                        <SelectTrigger data-testid="translate-language-select" className="h-9 w-48">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="original">Original</SelectItem>
                            <SelectItem value="Hindi">Hindi (हिन्दी)</SelectItem>
                            <SelectItem value="Marathi">Marathi (मराठी)</SelectItem>
                            <SelectItem value="Tamil">Tamil (தமிழ்)</SelectItem>
                            <SelectItem value="Spanish">Spanish</SelectItem>
                            <SelectItem value="French">French</SelectItem>
                            <SelectItem value="German">German</SelectItem>
                            <SelectItem value="Arabic">Arabic</SelectItem>
                            <SelectItem value="Chinese">Chinese (简体)</SelectItem>
                        </SelectContent>
                    </Select>
                    {translating && <span className="text-xs text-muted-foreground">Translating…</span>}
                </div>

                {showOriginal ? (
                    <EditableNotes
                        lecture={lecture}
                        isOwner={!!isOwner}
                        onSaved={onLectureUpdate}
                        renderNoteExtras={(i, text) => (
                            <BookmarkButton
                                lectureId={lecture.id}
                                kind="note"
                                refIndex={i}
                                text={text}
                                existing={findBookmark("note", i)}
                                onToggle={(bm) => onBookmarkToggle("note", i, bm)}
                            />
                        )}
                        renderConceptExtras={(i, text) => (
                            <BookmarkButton
                                lectureId={lecture.id}
                                kind="concept"
                                refIndex={i}
                                text={text}
                                size={14}
                                existing={findBookmark("concept", i)}
                                onToggle={(bm) => onBookmarkToggle("concept", i, bm)}
                            />
                        )}
                    />
                ) : (
                    <>
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
                                    <span>{n}</span>
                                </li>
                            ))}
                        </ul>
                        {m.key_concepts?.length > 0 && (
                            <div className="mt-8">
                                <h3 className="text-overline mb-3 text-muted-foreground">Key concepts</h3>
                                <div className="flex flex-wrap gap-2">
                                    {m.key_concepts.map((c, i) => (
                                        <span
                                            key={i}
                                            className="border border-primary/20 bg-accent/20 px-3 py-1 text-sm font-medium"
                                        >
                                            {c}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </>
                )}
            </TabsContent>

            <TabsContent value="quiz" className="mt-8" data-testid="quiz-tab-content">
                <QuizRunner lectureId={lecture.id} quiz={baseMaterials.quiz || []} />
            </TabsContent>

            <TabsContent value="flashcards" className="mt-8" data-testid="flashcards-tab-content">
                <FlashcardDeck cards={m.flashcards || []} lectureId={showOriginal ? lecture.id : null} />
            </TabsContent>

            <TabsContent value="chat" className="mt-8" data-testid="chat-tab-content">
                <DoubtChat lectureId={lecture.id} canChat={!!lecture.transcript} />
            </TabsContent>

            <TabsContent value="transcript" className="mt-8" data-testid="transcript-tab-content">
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground/85">
                    {lecture.transcript || "No transcript available."}
                </pre>
            </TabsContent>
        </Tabs>
    );
}
