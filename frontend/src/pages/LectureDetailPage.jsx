import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { lectureApi, API } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import AppShell from "@/components/AppShell";
import FlashcardDeck from "@/components/FlashcardDeck";
import QuizRunner from "@/components/QuizRunner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Lightning,
    CheckCircle,
    WarningCircle,
    PaperPlaneTilt,
    Trash,
    EyeSlash,
} from "@phosphor-icons/react";
import { toast } from "sonner";

const STATUS_LABEL = {
    uploaded: "Queued",
    processing: "AI is processing",
    ready: "Ready",
    error: "Error",
};

export default function LectureDetailPage() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { user } = useAuth();
    const [lecture, setLecture] = useState(null);
    const [audioToken, setAudioToken] = useState(null);

    useEffect(() => {
        let cancelled = false;
        let timer;
        const load = async () => {
            try {
                const data = await lectureApi.get(id);
                if (cancelled) return;
                setLecture(data);
                if (data.status === "processing" || data.status === "uploaded") {
                    timer = setTimeout(load, 4000);
                }
            } catch (err) {
                toast.error(err?.response?.data?.detail || "Failed to load lecture");
                navigate(-1);
            }
        };
        load();
        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
    }, [id, navigate]);

    // produce an authed audio url via blob since FastAPI auth is via header
    useEffect(() => {
        if (!lecture) return;
        const token = localStorage.getItem("lm_token");
        fetch(`${API}/lectures/${lecture.id}/audio`, {
            headers: { Authorization: `Bearer ${token}` },
        })
            .then((r) => (r.ok ? r.blob() : Promise.reject(r)))
            .then((blob) => setAudioToken(URL.createObjectURL(blob)))
            .catch(() => setAudioToken(null));
    }, [lecture?.id, lecture?.status]);

    if (!lecture) {
        return (
            <AppShell>
                <div className="h-40 animate-pulse border border-border bg-muted/40" />
            </AppShell>
        );
    }

    const isOwner = user?.role === "teacher" && user.id === lecture.teacher_id;
    const ready = lecture.status === "ready";

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
            navigate("/teacher");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Delete failed");
        }
    };

    return (
        <AppShell>
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
                                className={
                                    lecture.status === "ready"
                                        ? "bg-primary text-primary-foreground"
                                        : lecture.status === "error"
                                            ? "bg-destructive text-destructive-foreground"
                                            : "bg-accent/30 text-accent-foreground"
                                }
                            >
                                {lecture.status === "ready" ? (
                                    <CheckCircle size={14} weight="duotone" className="mr-1" />
                                ) : lecture.status === "error" ? (
                                    <WarningCircle size={14} weight="duotone" className="mr-1" />
                                ) : (
                                    <Lightning size={14} weight="duotone" className="mr-1" />
                                )}
                                {STATUS_LABEL[lecture.status]}
                            </Badge>
                            {lecture.published && (
                                <Badge className="bg-accent text-accent-foreground">Published</Badge>
                            )}
                        </div>
                    </div>

                    {isOwner && (
                        <div className="flex gap-2">
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

            {lecture.status === "processing" || lecture.status === "uploaded" ? (
                <ProcessingState />
            ) : lecture.status === "error" ? (
                <ErrorState message={lecture.error_message} />
            ) : (
                <ContentTabs lecture={lecture} />
            )}
        </AppShell>
    );
}

function ProcessingState() {
    return (
        <div className="grid place-items-center border-2 border-dashed border-border bg-card p-16 text-center">
            <div className="flex h-16 w-16 animate-pulse items-center justify-center bg-accent">
                <Lightning size={32} weight="duotone" className="text-accent-foreground" />
            </div>
            <h3 className="font-display mt-5 text-2xl font-black tracking-tighter">
                AI is digesting your lecture
            </h3>
            <p className="mt-2 max-w-md text-muted-foreground">
                Transcribing audio, extracting concepts, and generating notes, quizzes, and
                flashcards. This usually takes a minute or two.
            </p>
        </div>
    );
}

function ErrorState({ message }) {
    return (
        <div className="border-2 border-destructive bg-destructive/10 p-8">
            <div className="flex items-center gap-3">
                <WarningCircle size={24} weight="duotone" className="text-destructive" />
                <h3 className="font-display text-2xl font-black tracking-tighter">
                    Processing failed
                </h3>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
                {message || "Something went wrong while processing this lecture."}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
                Verify that <code className="font-mono">GEMINI_API_KEY</code> is set in
                <code className="font-mono"> backend/.env</code> and try uploading again.
            </p>
        </div>
    );
}

function ContentTabs({ lecture }) {
    const m = lecture.materials || {};
    return (
        <Tabs defaultValue="notes" className="w-full" data-testid="lecture-tabs">
            <TabsList className="h-auto w-full justify-start gap-6 rounded-none border-b border-border bg-transparent p-0">
                {[
                    ["notes", "Smart Notes"],
                    ["quiz", "Quiz"],
                    ["flashcards", "Flashcards"],
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
            </TabsContent>

            <TabsContent value="quiz" className="mt-8" data-testid="quiz-tab-content">
                <QuizRunner lectureId={lecture.id} quiz={m.quiz || []} />
            </TabsContent>

            <TabsContent value="flashcards" className="mt-8" data-testid="flashcards-tab-content">
                <FlashcardDeck cards={m.flashcards || []} />
            </TabsContent>

            <TabsContent value="transcript" className="mt-8" data-testid="transcript-tab-content">
                <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground/85">
                    {lecture.transcript || "No transcript available."}
                </pre>
            </TabsContent>
        </Tabs>
    );
}
