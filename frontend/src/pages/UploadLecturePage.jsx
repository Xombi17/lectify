import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { lectureApi } from "@/lib/api";
import AppShell from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Microphone, UploadSimple, FileAudio } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function UploadLecturePage() {
    const navigate = useNavigate();
    const [title, setTitle] = useState("");
    const [subject, setSubject] = useState("");
    const [semester, setSemester] = useState("");
    const [file, setFile] = useState(null);
    const [progress, setProgress] = useState(0);
    const [submitting, setSubmitting] = useState(false);

    const onFile = (e) => {
        const f = e.target.files?.[0];
        if (!f) return;
        setFile(f);
        if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
    };

    const submit = async (e) => {
        e.preventDefault();
        if (!file) return toast.error("Pick an audio file first");
        const fd = new FormData();
        fd.append("title", title);
        fd.append("file", file);
        if (subject) fd.append("subject", subject);
        if (semester) fd.append("semester", semester);
        setSubmitting(true);
        setProgress(0);
        try {
            const lec = await lectureApi.upload(fd, (evt) => {
                if (evt.total) setProgress(Math.round((evt.loaded * 100) / evt.total));
            });
            toast.success("Uploaded — AI is processing your lecture");
            navigate(`/teacher/lectures/${lec.id}`);
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Upload failed");
            setSubmitting(false);
        }
    };

    return (
        <AppShell>
            <div className="mx-auto max-w-3xl">
                <div className="text-overline mb-3 text-primary">New lecture</div>
                <h1 className="font-display text-4xl font-black tracking-tighter sm:text-5xl">
                    Drop your recording.
                </h1>
                <p className="mt-3 text-muted-foreground">
                    MP3, WAV, M4A or any common audio format. Up to 200 MB.
                </p>

                <form onSubmit={submit} className="mt-10 space-y-6" data-testid="upload-form">
                    <FileDrop file={file} onFile={onFile} disabled={submitting} />

                    <div className="grid gap-5 md:grid-cols-2">
                        <div className="space-y-2 md:col-span-2">
                            <Label htmlFor="title">Lecture title</Label>
                            <Input
                                id="title"
                                data-testid="lecture-title-input"
                                placeholder="Operating Systems · Lecture 7 — Scheduling"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="subject">Subject (optional)</Label>
                            <Input
                                id="subject"
                                data-testid="lecture-subject-input"
                                placeholder="Operating Systems"
                                value={subject}
                                onChange={(e) => setSubject(e.target.value)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="semester">Semester (optional)</Label>
                            <Input
                                id="semester"
                                data-testid="lecture-semester-input"
                                placeholder="Fall 2026"
                                value={semester}
                                onChange={(e) => setSemester(e.target.value)}
                            />
                        </div>
                    </div>

                    {submitting && (
                        <div className="border border-border bg-card p-4">
                            <div className="text-overline mb-2 text-muted-foreground">
                                Uploading audio
                            </div>
                            <Progress value={progress} className="h-2" />
                            <div className="mt-2 text-xs text-muted-foreground">
                                {progress}% — once upload finishes, processing begins automatically.
                            </div>
                        </div>
                    )}

                    <div className="flex gap-3">
                        <Button
                            type="submit"
                            size="lg"
                            disabled={submitting || !file}
                            data-testid="submit-upload-btn"
                            className="transition-transform hover:scale-[1.02] active:scale-[0.98]"
                        >
                            <UploadSimple size={18} weight="duotone" className="mr-2" />
                            {submitting ? "Uploading…" : "Upload and process"}
                        </Button>
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => navigate("/teacher")}
                            data-testid="cancel-upload-btn"
                        >
                            Cancel
                        </Button>
                    </div>
                </form>
            </div>
        </AppShell>
    );
}

function FileDrop({ file, onFile, disabled }) {
    const [drag, setDrag] = useState(false);
    return (
        <label
            data-testid="audio-dropzone"
            onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                onFile({ target: { files: e.dataTransfer.files } });
            }}
            className={`block cursor-pointer border-2 border-dashed p-10 text-center transition-all ${
                drag
                    ? "border-primary bg-accent/20"
                    : file
                        ? "border-primary/50 bg-card"
                        : "border-border bg-card hover:border-primary/40"
            } ${disabled ? "pointer-events-none opacity-60" : ""}`}
        >
            <input
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={onFile}
                data-testid="audio-file-input"
            />
            {file ? (
                <div className="flex flex-col items-center gap-3">
                    <div className="flex h-14 w-14 items-center justify-center bg-primary text-primary-foreground">
                        <FileAudio size={28} weight="duotone" />
                    </div>
                    <div>
                        <div className="font-display text-lg font-bold">{file.name}</div>
                        <div className="text-xs text-muted-foreground">
                            {(file.size / 1024 / 1024).toFixed(2)} MB ·{" "}
                            {file.type || "audio file"}
                        </div>
                    </div>
                    <div className="text-overline text-muted-foreground">
                        Click to swap file
                    </div>
                </div>
            ) : (
                <div className="flex flex-col items-center gap-3">
                    <div className="flex h-14 w-14 items-center justify-center bg-accent">
                        <Microphone size={28} weight="duotone" />
                    </div>
                    <div className="font-display text-xl font-bold">
                        Drop lecture audio here
                    </div>
                    <div className="text-sm text-muted-foreground">
                        or click to browse · mp3 · wav · m4a · up to 200 MB
                    </div>
                </div>
            )}
        </label>
    );
}
