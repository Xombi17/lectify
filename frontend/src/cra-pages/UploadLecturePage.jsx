import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { academicApi, lectureApi, timetableApi, uploadToS3 } from "@/lib/api";
import { FALLBACK_NOTICE, isPresignedUnavailable, uploadErrorCopy } from "@/lib/uploadTransport";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Microphone, UploadSimple, FileAudio, WarningCircle } from "@/components/icons";
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
    const [fieldErrors, setFieldErrors] = useState({});

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
        setFieldErrors((fe) => ({ ...fe, classId: undefined }));
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
                // Deep link from the teacher dashboard ("Upload lecture" on a
                // class card) preselects that class here.
                const params = new URLSearchParams(window.location.search);
                const requested = params.get("class_id");
                if (requested) {
                    const found = list.find((c) => c.class_id === requested);
                    if (found) {
                        setSelectedClassId(found.class_id);
                        setSelectedSlotId("");
                        if (found.subject_name) setSubject(found.subject_name);
                        if (found.semester_label) setSemester(found.semester_label);
                        loadSlots(found.class_id);
                        return;
                    }
                }
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
        setFieldErrors((fe) => ({ ...fe, file: undefined }));
        if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
    };

    const submit = async (e) => {
        e.preventDefault();
        const errs = {};
        if (!selectedClassId) errs.classId = "Pick the class this lecture belongs to.";
        if (!file) errs.file = "Pick an audio file to upload.";
        setFieldErrors(errs);
        if (errs.classId || errs.file) return;

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
        <div className="mx-auto max-w-2xl">
            <header className="mb-8">
                <div className="hand text-primary">New lecture</div>
                <h1 className="text-display">Upload lecture</h1>
                <p className="lede mt-3">
                    Add the recording and pick the class. Notes, a quiz and flashcards are ready once processing finishes.
                </p>
            </header>

            {!loadingClasses && assignedClasses.length === 0 && (
                <div data-testid="no-classes-warning" className="empty mt-6">
                    <WarningCircle aria-hidden="true" size={20} weight="bold" className="text-amber" />
                    <h2 className="text-2xl font-bold">No assigned classes found.</h2>
                    <p className="text-sm text-muted-foreground">
                        You have not been assigned to any classes yet. Contact an administrator to assign classes before uploading lectures.
                    </p>
                </div>
            )}

            <form onSubmit={submit} className="grid gap-6" data-testid="upload-form">
                <FileDrop file={file} onFile={onFile} error={fieldErrors.file} disabled={submitting || (!loadingClasses && assignedClasses.length === 0)} />

                <div className="grid gap-6 md:grid-cols-2">
                    {/* Class Selector Dropdown */}
                    <div className="grid gap-2 md:col-span-2">
                        <Label htmlFor="classId">Assigned class</Label>
                        <select
                            id="classId"
                            data-testid="class-select"
                            className="field"
                            value={selectedClassId}
                            onChange={(e) => handleClassChange(e.target.value)}
                            aria-invalid={fieldErrors.classId ? "true" : undefined}
                            aria-describedby={fieldErrors.classId ? "class-error" : undefined}
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
                        {fieldErrors.classId && (
                            <p id="class-error" className="errm" role="alert">
                                <WarningCircle aria-hidden="true" size={16} weight="bold" />
                                {fieldErrors.classId}
                            </p>
                        )}
                    </div>

                    {/* Optional Timetable Slot Dropdown */}
                    {timetableSlots.length > 0 && (
                        <div className="grid gap-2 md:col-span-2">
                            <Label htmlFor="slotId">Weekly Timetable Slot (optional)</Label>
                            <select
                                id="slotId"
                                data-testid="timetable-slot-select"
                                className="field"
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

                    <div className="grid gap-2 md:col-span-2">
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
                    <div className="grid gap-2">
                        <Label htmlFor="subject">Subject (optional)</Label>
                        <Input
                            id="subject"
                            data-testid="lecture-subject-input"
                            placeholder="Operating Systems"
                            value={subject}
                            onChange={(e) => setSubject(e.target.value)}
                        />
                    </div>
                    <div className="grid gap-2">
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
                    <div className="slip">
                        <div className="text-overline mb-2 text-muted-foreground">
                            {verifying ? "Verifying upload…" : "Uploading to storage…"}
                        </div>
                        <Progress value={progress} />
                        <div className="mt-2 font-mono text-sm text-muted-foreground">
                            {verifying
                                ? "Verifying upload…"
                                : `${progress}% — once upload finishes, processing begins automatically.`}
                        </div>
                    </div>
                )}

                {fallbackNotice && (
                    <div data-testid="fallback-notice" className="rounded-[var(--r)] border border-border bg-muted p-3 text-sm text-muted-foreground">
                        {fallbackNotice}
                    </div>
                )}

                {uploadError && (
                    <div data-testid="upload-error" role="alert" className="flex items-start gap-2 rounded-[var(--r)] border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                        <WarningCircle aria-hidden="true" size={16} weight="bold" className="mt-0.5 shrink-0" />
                        {uploadError}
                    </div>
                )}

                <div className="flex flex-wrap gap-3 border-t border-border pt-6">
                    <Button
                        type="submit"
                        variant="pen"
                        size="lg"
                        disabled={submitting || assignedClasses.length === 0}
                        data-testid="submit-upload-btn"
                    >
                        <UploadSimple size="1em" aria-hidden="true" weight="bold" />
                        {submitting ? "Uploading…" : "Upload lecture"}
                    </Button>
                    <Button
                        type="button"
                        variant="quiet"
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

function FileDrop({ file, onFile, disabled, error }) {
    const [drag, setDrag] = useState(false);
    return (
        <div>
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
                className={`empty block cursor-pointer focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ink ${
                    drag ? "bg-accent/20" : ""
                } ${error ? "border-destructive" : ""} ${disabled ? "pointer-events-none opacity-60" : ""}`}
            >
                <input
                    type="file"
                    accept="audio/*"
                    className="sr-only"
                    onChange={onFile}
                    aria-invalid={error ? "true" : undefined}
                    aria-describedby={error ? "file-error" : undefined}
                    data-testid="audio-file-input"
                />
                {file ? (
                    <div className="flex flex-col items-center gap-2">
                        <FileAudio aria-hidden="true" size={28} weight="bold" />
                        <div className="font-display max-w-full break-all text-xl">{file.name}</div>
                        <div className="font-mono text-sm text-muted-foreground">
                            {(file.size / 1024 / 1024).toFixed(2)} MB · {file.type || "audio file"}
                        </div>
                        <div className="text-sm text-muted-foreground">Click to swap file</div>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-2">
                        <Microphone aria-hidden="true" size={28} weight="bold" />
                        <div className="font-display text-xl">Drop lecture audio here</div>
                        <div className="text-sm text-muted-foreground">
                            or click to browse · mp3 · wav · m4a · up to 200 MB
                        </div>
                    </div>
                )}
            </label>
            {error && (
                <p id="file-error" className="errm mt-2" role="alert">
                    <WarningCircle aria-hidden="true" size={16} weight="bold" />
                    {error}
                </p>
            )}
        </div>
    );
}
