"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { academicApi, lectureApi, timetableApi, uploadToS3 } from "@/lib/api";
import { FALLBACK_NOTICE, isPresignedUnavailable, uploadErrorCopy } from "@/lib/uploadTransport";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Microphone, UploadSimple, FileAudio, WarningCircle } from "@phosphor-icons/react";
import { toast } from "sonner";

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function UploadLecturePage() {
    const router = useRouter();
    const [title, setTitle] = useState("");
    const [subject, setSubject] = useState("");
    const [semester, setSemester] = useState("");
    const [file, setFile] = useState(null);
    const [progress, setProgress] = useState(0);
    const [submitting, setSubmitting] = useState(false);
    const [verifying, setVerifying] = useState(false);
    const [fallbackNotice, setFallbackNotice] = useState("");
    const [uploadError, setUploadError] = useState("");

    // Class scoping & timetable slot state
    const [assignedClasses, setAssignedClasses] = useState([]);
    const [selectedClassId, setSelectedClassId] = useState("");
    const [loadingClasses, setLoadingClasses] = useState(true);
    const [timetableSlots, setTimetableSlots] = useState([]);
    const [selectedSlotId, setSelectedSlotId] = useState("");

    const loadSlots = async (classId) => {
        if (!classId) {
            setTimetableSlots([]);
            return;
        }
        try {
            const slots = await timetableApi.getClassTimetable(classId);
            setTimetableSlots(slots || []);
        } catch {
            setTimetableSlots([]);
        }
    };

    const handleClassChange = (classId) => {
        setSelectedClassId(classId);
        setSelectedSlotId("");
        const found = assignedClasses.find((c) => c.class_id === classId);
        if (found) {
            if (found.subject_name) setSubject(found.subject_name);
            if (found.semester_label) setSemester(found.semester_label);
        }
        loadSlots(classId);
    };

    useEffect(() => {
        academicApi
            .getMyAssignedClasses()
            .then((classes) => {
                const list = classes || [];
                setAssignedClasses(list);
                if (list.length === 1) {
                    const single = list[0];
                    setSelectedClassId(single.class_id);
                    if (single.subject_name) setSubject(single.subject_name);
                    if (single.semester_label) setSemester(single.semester_label);
                    loadSlots(single.class_id);
                }
            })
            .catch(() => {
                setAssignedClasses([]);
            })
            .finally(() => {
                setLoadingClasses(false);
            });
    }, []);

    const onFile = (e) => {
        const f = e.target.files?.[0];
        if (!f) return;
        setFile(f);
        if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
    };

    const submit = async (e) => {
        e.preventDefault();
        if (!selectedClassId) return toast.error("Please select an assigned class first");
        if (!file) return toast.error("Pick an audio file first");

        setSubmitting(true);
        setProgress(0);
        setVerifying(false);
        setFallbackNotice("");
        setUploadError("");
        const onProgress = (evt) => {
            if (evt.total) setProgress(Math.round((evt.loaded * 100) / evt.total));
        };

        const showError = (message) => {
            setUploadError(message);
            toast.error(message);
            setSubmitting(false);
            setVerifying(false);
        };

        // Prefer browser-direct S3 upload; fall back to multipart on 501.
        let presigned = null;
        try {
            presigned = await lectureApi.uploadUrl({
                title,
                class_id: selectedClassId,
                timetable_slot_id: selectedSlotId || undefined,
                subject: subject || undefined,
                semester: semester || undefined,
                filename: file.name,
                content_type: file.type || "audio/mpeg",
                size: file.size,
            });
        } catch (err) {
            if (isPresignedUnavailable(err)) {
                setFallbackNotice(FALLBACK_NOTICE);
            } else {
                return showError(uploadErrorCopy(err));
            }
        }

        if (!presigned) {
            // Multipart fallback path (LocalStorage / dev).
            const fd = new FormData();
            fd.append("title", title);
            fd.append("file", file);
            fd.append("class_id", selectedClassId);
            if (selectedSlotId) fd.append("timetable_slot_id", selectedSlotId);
            if (subject) fd.append("subject", subject);
            if (semester) fd.append("semester", semester);
            try {
                const lec = await lectureApi.upload(fd, onProgress);
                toast.success("Uploaded — AI is processing your lecture");
                router.push(`/teacher/lectures/${lec.id}`);
            } catch (err) {
                showError(err?.response?.data?.detail || "Upload failed");
            }
            return;
        }

        try {
            await uploadToS3(presigned, file, (loaded, total) => {
                if (total) setProgress(Math.round((loaded * 100) / total));
            });
            setVerifying(true);
            const lec = await lectureApi.uploadComplete(presigned.lecture_id);
            toast.success("Upload complete — processing started");
            router.push(`/teacher/lectures/${lec.id}`);
        } catch (err) {
            showError(uploadErrorCopy(err));
        }
    };

    return (
        <div className="mx-auto max-w-4xl animate-in">
            <section className="page-intro">
                <div>
                    <div className="eyebrow text-accent">New lecture</div>
                    <h1>Drop your recording.</h1>
                    <p>Upload common audio formats up to 200 MB. We&apos;ll keep you updated while the study material is prepared.</p>
                </div>
                <div className="hidden border border-border bg-card px-4 py-3 font-mono text-[0.64rem] uppercase tracking-[0.1em] text-muted-foreground sm:block">browser → storage<br /><span className="text-accent">direct upload</span></div>
            </section>

            {!loadingClasses && assignedClasses.length === 0 && (
                <div
                    data-testid="no-classes-warning"
                    className="mt-6 flex items-start gap-3 border border-[hsl(var(--warning)/.35)] bg-[hsl(var(--warning)/.08)] p-4 text-sm text-[hsl(var(--warning))]"
                >
                    <WarningCircle size={20} weight="fill" className="shrink-0 mt-0.5 text-amber-600" />
                    <div>
                        <div className="font-bold">No assigned classes found.</div>
                        <div>
                            You have not been assigned to any classes yet. Contact an administrator to assign classes before uploading lectures.
                        </div>
                    </div>
                </div>
            )}

            <form onSubmit={submit} className="mt-8 space-y-7" data-testid="upload-form">
                <FileDrop file={file} onFile={onFile} disabled={submitting || (!loadingClasses && assignedClasses.length === 0)} />

                <div className="grid gap-5 md:grid-cols-2">
                    {/* Class Selector Dropdown */}
                    <div className="space-y-2 md:col-span-2">
                        <Label htmlFor="classId">Assigned Class *</Label>
                        <select
                            id="classId"
                            data-testid="class-select"
                            className="flex h-11 w-full rounded-lg border border-input bg-card px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                            value={selectedClassId}
                            onChange={(e) => handleClassChange(e.target.value)}
                            required
                            disabled={submitting || loadingClasses || assignedClasses.length === 0}
                        >
                            <option value="">
                                {loadingClasses
                                    ? "Loading assigned classes…"
                                    : assignedClasses.length === 0
                                    ? "No classes assigned"
                                    : "Select an assigned class…"}
                            </option>
                            {assignedClasses.map((c) => (
                                <option key={c.class_id} value={c.class_id}>
                                    {c.subject_name || "Subject"} · {c.division_name || "Division"} ({c.semester_label || "Semester"})
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Optional Timetable Slot Dropdown */}
                    {timetableSlots.length > 0 && (
                        <div className="space-y-2 md:col-span-2">
                            <Label htmlFor="slotId">Weekly Timetable Slot (optional)</Label>
                            <select
                                id="slotId"
                                data-testid="timetable-slot-select"
                                className="flex h-11 w-full rounded-lg border border-input bg-card px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                value={selectedSlotId}
                                onChange={(e) => setSelectedSlotId(e.target.value)}
                                disabled={submitting}
                            >
                                <option value="">No specific slot (general lecture)</option>
                                {timetableSlots.map((s) => (
                                    <option key={s.id} value={s.id}>
                                        {DAY_NAMES[s.day_of_week] || `Day ${s.day_of_week}`} · {s.start_time} - {s.end_time} {s.room ? `(${s.room})` : ""}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

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
                    <div className="surface-panel p-5">
                        <div className="eyebrow mb-2 text-muted-foreground">
                            {verifying ? "Verifying upload…" : "Uploading to storage…"}
                        </div>
                        <Progress value={progress} className="h-2" />
                        <div className="mt-2 text-xs text-muted-foreground">
                            {verifying
                                ? "Verifying upload…"
                                : `${progress}% — once upload finishes, processing begins automatically.`}
                        </div>
                    </div>
                )}

                {fallbackNotice && (
                    <div data-testid="fallback-notice" className="border border-border bg-muted/45 p-4 text-sm leading-6 text-muted-foreground">
                        {fallbackNotice}
                    </div>
                )}

                {uploadError && (
                    <div data-testid="upload-error" role="alert" className="border border-destructive/40 bg-destructive/10 p-4 text-sm leading-6 text-destructive">
                        {uploadError}
                    </div>
                )}

                <div className="flex gap-3">
                    <Button
                        type="submit"
                        size="lg"
                        disabled={submitting || !file || !selectedClassId || assignedClasses.length === 0}
                        data-testid="submit-upload-btn"
                        className="transition-transform hover:scale-[1.02] active:scale-[0.98]"
                    >
                        <UploadSimple size={18} weight="duotone" className="mr-2" />
                        {submitting ? "Uploading…" : "Upload and process"}
                    </Button>
                    <Button
                        type="button"
                        variant="ghost"
                        onClick={() => router.push("/teacher/dashboard")}
                        data-testid="cancel-upload-btn"
                    >
                        Cancel
                    </Button>
                </div>
            </form>
        </div>
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
            className={`block cursor-pointer border-2 border-dashed bg-card p-10 text-center transition-all sm:p-14 ${
                drag
                    ? "border-accent bg-accent/10"
                    : file
                        ? "border-accent/60"
                        : "border-border hover:border-accent/60"
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
                    <div className="flex h-14 w-14 items-center justify-center bg-[hsl(var(--shell-rail))] text-accent">
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
                    <div className="flex h-14 w-14 items-center justify-center bg-accent text-accent-foreground">
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
