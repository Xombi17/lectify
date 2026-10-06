import { useEffect, useState } from "react";
import Link from "next/link";
import { lectureApi, timetableApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Microphone,
    BookOpen,
    Lightning,
    CheckCircle,
    WarningCircle,
    Clock,
    Calendar,
} from "@phosphor-icons/react";
import { motion } from "framer-motion";

const EMPTY_IMG =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect fill='%23f8f9fa' width='400' height='300'/%3E%3Cpath d='M120 100h160v100H120z' fill='%23ddd'/%3E%3Cpath d='M140 130h120v4H140zM140 145h100v3H140zM140 160h80v3H140z' fill='%23bbb'/%3E%3C/svg%3E";

const STATUS = {
    uploaded: { label: "Queued", icon: Clock, cls: "bg-muted text-muted-foreground" },
    processing: { label: "Processing", icon: Lightning, cls: "bg-accent/30 text-accent-foreground" },
    ready: { label: "Ready", icon: CheckCircle, cls: "bg-primary text-primary-foreground" },
    error: { label: "Error", icon: WarningCircle, cls: "bg-destructive text-destructive-foreground" },
};

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function TeacherDashboard() {
    const [lectures, setLectures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [schedule, setSchedule] = useState([]);

    const load = async () => {
        try {
            setLectures(await lectureApi.mine());
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
        timetableApi.getMySchedule().then((s) => setSchedule(s || [])).catch(() => setSchedule([]));
        const t = setInterval(load, 8000); // poll while processing
        return () => clearInterval(t);
    }, []);

    const stats = {
        total: lectures.length,
        ready: lectures.filter((l) => l.status === "ready").length,
        processing: lectures.filter((l) => l.status === "processing" || l.status === "uploaded").length,
        published: lectures.filter((l) => l.published).length,
    };

    return (
        <section className="mb-10 flex flex-col items-start justify-between gap-6 md:flex-row md:items-end">
                <div>
                    <div className="text-overline mb-3 text-primary">Teacher dashboard</div>
                    <h1 className="font-display text-4xl font-black tracking-tighter sm:text-5xl">
                        Your lecture library.
                    </h1>
                    <p className="mt-3 max-w-xl text-base text-muted-foreground">
                        Drop a recording. We&apos;ll transcribe it, build clean notes, write a
                        quiz, and cut flashcards — automatically.
                    </p>
                </div>
                <Link to="/teacher/upload">
                    <Button
                        size="lg"
                        data-testid="upload-lecture-btn"
                        className="transition-transform hover:scale-[1.02] active:scale-[0.98]"
                    >
                        <Microphone size={18} weight="duotone" className="mr-2" />
                        Upload lecture
                    </Button>
                </Link>
            </section>

            {/* Stats bento */}
            <section className="mb-10 grid grid-cols-2 gap-4 md:grid-cols-4">
                {[
                    { label: "Total lectures", value: stats.total, accent: false },
                    { label: "Ready to publish", value: stats.ready, accent: false },
                    { label: "In processing", value: stats.processing, accent: false },
                    { label: "Published", value: stats.published, accent: true },
                ].map((s) => (
                    <div
                        key={s.label}
                        data-testid={`stat-${s.label.toLowerCase().replace(/\s/g, "-")}`}
                        className={`border border-border p-6 transition-all hover:border-primary/30 ${
                            s.accent ? "bg-primary text-primary-foreground" : "bg-card"
                        }`}
                    >
                        <div
                            className={`text-overline ${
                                s.accent ? "text-accent" : "text-muted-foreground"
                            }`}
                        >
                            {s.label}
                        </div>
                        <div className="mt-2 font-display text-4xl font-black tracking-tighter">
                            {s.value}
                        </div>
                    </div>
                ))}
            </section>

            {/* Teaching Schedule */}
            {schedule.length > 0 && (
                <section className="mb-10" data-testid="teacher-schedule">
                    <div className="mb-4 flex items-center justify-between border-b border-border pb-2">
                        <div className="flex items-center gap-2">
                            <Calendar size={20} weight="duotone" className="text-primary" />
                            <h2 className="font-display text-xl font-bold tracking-tight">
                                Weekly teaching schedule
                            </h2>
                        </div>
                        <span className="text-overline text-muted-foreground">
                            {schedule.length} session{schedule.length === 1 ? "" : "s"}
                        </span>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                        {[...schedule]
                            .sort((a, b) => a.day_of_week - b.day_of_week || a.start_time.localeCompare(b.start_time))
                            .map((slot) => (
                                <div
                                    key={slot.id}
                                    data-testid={`schedule-slot-${slot.id}`}
                                    className="border border-border bg-card p-4 transition-all hover:border-primary/40"
                                >
                                    <div className="flex items-center justify-between">
                                        <Badge variant="secondary" className="font-semibold">
                                            {DAY_NAMES[slot.day_of_week] || `Day ${slot.day_of_week}`}
                                        </Badge>
                                        {slot.room && (
                                            <span className="text-xs text-muted-foreground">
                                                {slot.room}
                                            </span>
                                        )}
                                    </div>
                                    <div className="mt-3 flex items-center gap-2 text-sm font-bold font-display">
                                        <Clock size={16} weight="duotone" className="text-primary" />
                                        <span>{slot.start_time} - {slot.end_time}</span>
                                    </div>
                                </div>
                            ))}
                    </div>
                </section>
            )}

            {/* List */}
            <section data-testid="lectures-list">
                <div className="mb-4 flex items-center justify-between border-b border-border pb-2">
                    <h2 className="font-display text-xl font-bold tracking-tight">
                        Recent lectures
                    </h2>
                    <span className="text-overline text-muted-foreground">
                        Auto-refreshing
                    </span>
                </div>

                {loading ? (
                    <div className="grid gap-3">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-24 animate-pulse border border-border bg-muted/40" />
                        ))}
                    </div>
                ) : lectures.length === 0 ? (
                    <EmptyState />
                ) : (
                    <div className="grid gap-3">
                        {lectures.map((l, idx) => {
                            const s = STATUS[l.status] || STATUS.uploaded;
                            const Icon = s.icon;
                            return (
                                <motion.div
                                    key={l.id}
                                    initial={{ opacity: 0, y: 8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: idx * 0.04 }}
                                >
                                    <Link
                                        href={`/teacher/lectures/${l.id}`}
                                        data-testid={`lecture-row-${l.id}`}
                                        className="group flex items-center justify-between gap-4 border border-border bg-card px-5 py-4 transition-all hover:border-primary/40 hover:shadow-sm"
                                    >
                                        <div className="flex min-w-0 flex-1 items-center gap-4">
                                            <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-muted">
                                                <BookOpen
                                                    size={20}
                                                    weight="duotone"
                                                    className="text-primary"
                                                />
                                            </div>
                                            <div className="min-w-0 flex-1">
                                                <div className="truncate font-display text-base font-bold">
                                                    {l.title}
                                                </div>
                                                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                                                    {l.subject && (
                                                        <span>{l.subject}</span>
                                                    )}
                                                    {l.semester && (
                                                        <span>· {l.semester}</span>
                                                    )}
                                                    <span>
                                                        · {new Date(l.created_at).toLocaleDateString()}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            {l.published && (
                                                <Badge variant="outline" className="border-primary text-primary">
                                                    Published
                                                </Badge>
                                            )}
                                            <span
                                                className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold ${s.cls}`}
                                            >
                                                <Icon size={14} weight="duotone" />
                                                {s.label}
                                            </span>
                                        </div>
                                    </Link>
                                </motion.div>
                            );
                        })}
                    </div>
                )}
            </section>
    );
}

function EmptyState() {
    return (
        <div className="grid grid-cols-1 items-center gap-6 border border-border bg-card p-10 md:grid-cols-2">
            <div>
                <div className="text-overline mb-2 text-primary">No lectures yet</div>
                <h3 className="font-display text-3xl font-black tracking-tighter">
                    Press record on your first lecture.
                </h3>
                <p className="mt-3 text-muted-foreground">
                    Upload any audio file (mp3, wav, m4a). LectureMind will do the rest.
                </p>
                <Link to="/teacher/upload" className="mt-6 inline-block">
                    <Button data-testid="empty-upload-btn">
                        <Microphone size={18} weight="duotone" className="mr-2" />
                        Upload lecture
                    </Button>
                </Link>
            </div>
            <img src={EMPTY_IMG} alt="Empty state" className="mx-auto h-60 object-contain" />
        </div>
    );
}
