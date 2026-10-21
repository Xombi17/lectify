"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { lectureApi, API, bookmarkApi } from "@/lib/api";
import { statusPillKind, FAILED_MESSAGE } from "@/lib/lectureStatus";
import { formatProcessing } from "@/lib/formatDuration";
import { useAuth } from "@/lib/auth";
import FlashcardDeck from "@/components/FlashcardDeck";
import QuizRunner from "@/components/QuizRunner";
import DoubtChat from "@/components/DoubtChat";
import EditableNotes from "@/components/EditableNotes";
import BookmarkButton from "@/components/BookmarkButton";
import StatusStamp from "@/components/StatusStamp";
import PenPlayer from "@/components/PenPlayer";
import { usePageTitle } from "@/lib/usePageTitle";
import { getPosition, rememberLecture, savePosition } from "@/lib/recentLectures";
import ConfirmDialog from "@/components/ConfirmDialog";
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
    ArrowLeft,
    Lightning,
    WarningCircle,
    PaperPlaneTilt,
    Trash,
    EyeSlash,
    Translate,
    DownloadSimple,
} from "@/components/icons";
import { toast } from "sonner";

export default function LectureDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { user } = useAuth();
    const [lecture, setLecture] = useState(null);
    const [audioToken, setAudioToken] = useState(null);
    const [downloadingPdf, setDownloadingPdf] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState(false);
    const [retrying, setRetrying] = useState(false);
    usePageTitle(lecture?.title || "Lecture");

    // Students resume playback where they stopped, and the library's "pick up where you left off" uses this too
    const isStudent = user?.role === "student";
    const startAt = useMemo(() => (isStudent && id ? getPosition(user.id, id) : 0), [isStudent, user?.id, id]);
    useEffect(() => {
        if (isStudent && lecture?.id) {
            rememberLecture(user.id, { id: lecture.id, title: lecture.title, subject: lecture.subject });
        }
    }, [isStudent, user?.id, lecture?.id, lecture?.title, lecture?.subject]);

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
            <div className="sk h-40" aria-busy="true" />
        );
    }

    const isOwner = user?.role === "teacher" && user.id === lecture.teacher_id;
    const ready = lecture.status === "ready";
    const pillKind = statusPillKind(lecture.status);
    const home = user?.role === "student" ? "/student/dashboard" : user?.role === "admin" ? "/admin" : "/teacher/dashboard";

    const retry = async () => {
        if (retrying) return;
        setRetrying(true);
        try {
            setLecture(await lectureApi.retry(lecture.id));
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Retry failed");
        } finally {
            setRetrying(false);
        }
    };

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
                <Link href={home} className="crumb">
                    <ArrowLeft size={16} weight="bold" aria-hidden="true" />
                    All lectures
                </Link>
                <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-end">
                    <div className="min-w-0 max-w-4xl">
                        <h1 className="text-display">{lecture.title}</h1>
                        <div className="meta mt-2">
                            {lecture.subject && <span>{lecture.subject}</span>}
                            {lecture.semester && <span>{lecture.semester}</span>}
                            {lecture.created_at && (
                                <time className="date" dateTime={lecture.created_at}>
                                    {new Date(lecture.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                                </time>
                            )}
                            <StatusStamp status={lecture.status} />
                            {ready && formatProcessing(lecture.processing_seconds) && (
                                <span data-testid="processing-time" className="date">
                                    Processed in {formatProcessing(lecture.processing_seconds)}
                                </span>
                            )}
                            {lecture.published && <span className="tag">Published</span>}
                        </div>
                    </div>

                    {isOwner && (
                        <div className="flex shrink-0 flex-wrap gap-2">
                            {ready && (
                                <Button
                                    variant="default"
                                    onClick={downloadPdf}
                                    disabled={downloadingPdf}
                                    data-testid="download-pdf-btn"
                                >
                                    <DownloadSimple size={16} weight="regular" className="mr-2" />
                                    {downloadingPdf ? "Preparing…" : "PDF"}
                                </Button>
                            )}
                            <Button
                                variant={lecture.published ? "default" : "pen"}
                                onClick={togglePublish}
                                disabled={!ready}
                                data-testid="publish-toggle-btn"
                            >
                                {lecture.published ? (
                                    <>
                                        <EyeSlash size={16} weight="regular" className="mr-2" />
                                        Unpublish
                                    </>
                                ) : (
                                    <>
                                        <PaperPlaneTilt size={16} weight="regular" className="mr-2" />
                                        Publish to students
                                    </>
                                )}
                            </Button>
                            <Button
                                variant="default"
                                className="text-destructive hover:text-destructive"
                                onClick={() => setConfirmDelete(true)}
                                data-testid="delete-lecture-btn"
                                aria-label="Delete lecture"
                            >
                                <Trash size={16} />
                            </Button>
                        </div>
                    )}
                </div>
            </div>

            {audioToken && pillKind !== "failed" && (
                <PenPlayer
                    src={audioToken}
                    startAt={startAt}
                    onProgress={isStudent ? (s) => savePosition(user.id, lecture.id, s) : undefined}
                />
            )}

            <ConfirmDialog
                open={confirmDelete}
                onOpenChange={setConfirmDelete}
                title={`Delete ${lecture.title}? This removes it and cannot be undone.`}
                confirmLabel="Delete lecture"
                cancelLabel="Keep it"
                onConfirm={remove}
            />

            {pillKind === "processing" ? (
                <ProcessingState lecture={lecture} />
            ) : pillKind === "failed" ? (
                <ErrorState canRetry={user?.role === "admin" || isOwner} onRetry={retry} retrying={retrying} />
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
        <div className="rounded-[var(--radius)] border border-border bg-card px-6 py-12 text-center sm:px-12">
            <div className="mx-auto mb-5 flex h-14 w-14 motion-safe:animate-pulse items-center justify-center rounded-full bg-accent">
                <Lightning size={28} weight="regular" className="text-primary" />
            </div>
            <h3 className="text-2xl font-bold">
                Writing up your lecture
            </h3>
            <p
                className="mt-2 text-sm text-muted-foreground"
                data-testid="processing-label"
            >
                {label}
            </p>

            {pct !== null && (
                <div className="mx-auto mt-6 max-w-md">
                    <div className="mb-2 flex items-center justify-between text-sm">
                        <span className="text-overline text-muted-foreground">Progress</span>
                        <span className="font-mono text-primary" data-testid="processing-percent">
                            {pct}%
                        </span>
                    </div>
                    <div
                        className="ink-line"
                        role="progressbar"
                        aria-label="Writing up"
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-valuenow={pct}
                    >
                        <span style={{ width: `${pct}%` }} data-testid="processing-bar" />
                    </div>
                    <div className="mt-1 text-sm text-muted-foreground">
                        Step {step} of {total}
                    </div>
                </div>
            )}

            {isLong && lecture.chunk_count > 0 && (
                <p className="mt-6 inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1 text-sm text-muted-foreground">
                    <Lightning size={12} weight="regular" />
                    Long lecture detected · split into{" "}
                    <span className="font-mono text-primary">{lecture.chunk_count}</span>{" "}
                    chunks for hierarchical processing
                </p>
            )}
        </div>
    );
}

function ErrorState({ canRetry, onRetry, retrying }) {
    return (
        <div role="alert" className="rounded-[var(--radius)] border border-destructive/50 bg-destructive/10 p-6 sm:p-8">
            <div className="flex items-center gap-3">
                <WarningCircle size={24} className="text-destructive" aria-hidden="true" />
                <h3 className="text-2xl font-bold">Processing failed</h3>
            </div>
            <p className="mt-3 text-base">{FAILED_MESSAGE}</p>
            {canRetry && (
                <Button variant="pen" className="mt-4" onClick={onRetry} disabled={retrying}>
                    Retry processing
                </Button>
            )}
        </div>
    );
}

function ContentTabs({ lecture, isOwner, onLectureUpdate }) {
    const baseMaterials = lecture.materials || {};
    const [language, setLanguage] = useState("original");
    const [translating, setTranslating] = useState(false);
    const [translated, setTranslated] = useState(null);
    const [activeTab, setActiveTab] = useState("notes");
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
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full" data-testid="lecture-tabs">
            <TabsList className="read-tabs">
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
                    >
                        {label}
                    </TabsTrigger>
                ))}
            </TabsList>

            <TabsContent value="notes" className="mt-8" data-testid="notes-tab-content">
                <div className="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
                    <div className="flex flex-wrap items-center gap-3">
                        <Translate size={16} weight="regular" className="text-primary" />
                        <span className="text-overline text-muted-foreground">View in</span>
                        <Select value={language} onValueChange={onLanguage} disabled={translating}>
                            <SelectTrigger data-testid="translate-language-select" className="w-48">
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
                        {translating && <span className="text-sm text-muted-foreground">Translating…</span>}
                    </div>
                </div>

                <EditableNotes
                    lecture={lecture}
                    materials={m}
                    isOwner={showOriginal ? !!isOwner : false}
                    onSaved={onLectureUpdate}
                    onTabChange={setActiveTab}
                    quizCount={(baseMaterials.quiz || []).length}
                    flashcardsCount={(m.flashcards || baseMaterials.flashcards || []).length}
                    hasTranscript={!!lecture.transcript}
                    renderNoteExtras={showOriginal ? (i, text) => (
                        <BookmarkButton
                            lectureId={lecture.id}
                            kind="note"
                            refIndex={i}
                            text={text}
                            existing={findBookmark("note", i)}
                            onToggle={(bm) => onBookmarkToggle("note", i, bm)}
                        />
                    ) : undefined}
                    renderConceptExtras={showOriginal ? (i, text) => (
                        <BookmarkButton
                            lectureId={lecture.id}
                            kind="concept"
                            refIndex={i}
                            text={text}
                            size={14}
                            existing={findBookmark("concept", i)}
                            onToggle={(bm) => onBookmarkToggle("concept", i, bm)}
                        />
                    ) : undefined}
                />
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
                <div className="rounded-xl border border-border bg-card p-6 sm:p-8 max-w-4xl shadow-sm">
                    <div className="mb-4 flex items-center justify-between border-b border-border pb-3">
                        <span className="text-overline text-muted-foreground uppercase">
                            Verbatim Lecture Transcript
                        </span>
                        <span className="font-mono text-sm text-muted-foreground">
                            {lecture.transcript ? `${lecture.transcript.split(/\s+/).filter(Boolean).length} words` : "0 words"}
                        </span>
                    </div>
                    <pre className="notes whitespace-pre-wrap font-sans text-base leading-relaxed text-foreground/90">
                        {lecture.transcript || "No transcript available."}
                    </pre>
                </div>
            </TabsContent>
        </Tabs>
    );
}
