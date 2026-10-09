"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { lectureApi, timetableApi } from "@/lib/api";
import { Calendar, CheckCircle, Clock, Lightning, Microphone, WarningCircle } from "@phosphor-icons/react";

const STATUS = {
    uploaded: { label: "Queued", icon: Clock, className: "border-border bg-muted text-muted-foreground" },
    processing: { label: "Processing", icon: Lightning, className: "border-[hsl(var(--warning)/.35)] bg-[hsl(var(--warning)/.1)] text-[hsl(var(--warning))]" },
    ready: { label: "Ready", icon: CheckCircle, className: "border-[hsl(var(--success)/.35)] bg-[hsl(var(--success)/.1)] text-[hsl(var(--success))]" },
    error: { label: "Needs attention", icon: WarningCircle, className: "border-destructive/30 bg-destructive/10 text-destructive" },
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
        timetableApi.getMySchedule().then((items) => setSchedule(items || [])).catch(() => setSchedule([]));
        const timer = setInterval(load, 8000);
        return () => clearInterval(timer);
    }, []);

    const stats = {
        total: lectures.length,
        ready: lectures.filter((lecture) => lecture.status === "ready").length,
        processing: lectures.filter((lecture) => lecture.status === "processing" || lecture.status === "uploaded").length,
        published: lectures.filter((lecture) => lecture.published).length,
    };

    return (
        <div className="animate-in">
            <section className="page-intro">
                <div>
                    <div className="eyebrow text-accent">Teacher workspace</div>
                    <h1>Your lecture desk.</h1>
                    <p>Upload a recording, track its progress, and publish the study material when it is ready for your class.</p>
                </div>
                <Link href="/teacher/upload"><Button size="lg" data-testid="upload-lecture-btn" className="h-11 shrink-0 font-bold"><Microphone size={18} weight="bold" /> Upload lecture</Button></Link>
            </section>

            <section aria-label="Lecture overview" className="grid grid-cols-2 gap-px overflow-hidden border border-border bg-border md:grid-cols-4">
                {[
                    { label: "Total lectures", value: stats.total },
                    { label: "Ready to publish", value: stats.ready },
                    { label: "In progress", value: stats.processing },
                    { label: "Published", value: stats.published, accent: true },
                ].map((stat) => (
                    <div key={stat.label} className={`p-5 sm:p-6 ${stat.accent ? "bg-accent text-accent-foreground" : "bg-card"}`} data-testid={`stat-${stat.label.toLowerCase().replace(/\s/g, "-")}`}>
                        <div className={`eyebrow ${stat.accent ? "text-accent-foreground/75" : "text-muted-foreground"}`}>{stat.label}</div>
                        <strong className="mt-2 block font-display text-4xl font-extrabold tracking-[-0.07em]">{stat.value}</strong>
                    </div>
                ))}
            </section>

            {schedule.length > 0 && <section className="mt-10" data-testid="teacher-schedule">
                <div className="mb-4 flex items-center justify-between border-b border-border pb-3"><div className="flex items-center gap-2"><Calendar size={18} className="text-accent" weight="bold" /><h2 className="text-lg font-extrabold tracking-[-0.04em]">This week</h2></div><span className="font-mono text-[0.64rem] uppercase tracking-[0.12em] text-muted-foreground">{schedule.length} session{schedule.length === 1 ? "" : "s"}</span></div>
                <div className="grid gap-px overflow-hidden border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
                    {[...schedule].sort((a, b) => a.day_of_week - b.day_of_week || a.start_time.localeCompare(b.start_time)).map((slot) => <div key={slot.id} data-testid={`schedule-slot-${slot.id}`} className="bg-card p-4"><div className="flex items-center justify-between gap-3"><Badge variant="secondary" className="font-semibold">{DAY_NAMES[slot.day_of_week] || `Day ${slot.day_of_week}`}</Badge>{slot.room && <span className="font-mono text-[0.65rem] text-muted-foreground">{slot.room}</span>}</div><div className="mt-4 flex items-center gap-2 text-sm font-bold"><Clock size={15} className="text-accent" weight="bold" /> {slot.start_time}–{slot.end_time}</div></div>)}
                </div>
            </section>}

            <section className="mt-10" data-testid="lectures-list">
                <div className="mb-4 flex items-center justify-between border-b border-border pb-3"><div><h2 className="text-lg font-extrabold tracking-[-0.04em]">Recent lectures</h2><p className="mt-1 text-sm text-muted-foreground">Status refreshes automatically while AI is processing.</p></div><span className="font-mono text-[0.64rem] uppercase tracking-[0.12em] text-muted-foreground">{lectures.length} records</span></div>
                {loading ? <LoadingRows /> : lectures.length === 0 ? <EmptyState /> : <div className="overflow-hidden border border-border">
                    {lectures.map((lecture, index) => {
                        const status = STATUS[lecture.status] || STATUS.uploaded;
                        const Icon = status.icon;
                        return <motion.div key={lecture.id} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.035 }}><Link href={`/teacher/lectures/${lecture.id}`} data-testid={`lecture-row-${lecture.id}`} className="data-row flex flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5"><div className="flex min-w-0 items-center gap-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center bg-muted text-accent"><span className="font-mono text-xs font-bold">{String(index + 1).padStart(2, "0")}</span></span><span className="min-w-0"><span className="block truncate font-display text-base font-extrabold tracking-[-0.03em]">{lecture.title}</span><span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">{lecture.subject && <span>{lecture.subject}</span>}{lecture.semester && <span>· {lecture.semester}</span>}<span>· {new Date(lecture.created_at).toLocaleDateString()}</span></span></span></div><div className="flex items-center gap-3 pl-[60px] sm:pl-0">{lecture.published && <Badge variant="outline" className="border-[hsl(var(--success)/.4)] text-[hsl(var(--success))]">Published</Badge>}<span className={`status-chip ${status.className}`}><Icon size={13} weight="bold" /> {status.label}</span></div></Link></motion.div>;
                    })}
                </div>}
            </section>
        </div>
    );
}

function LoadingRows() {
    return <div className="space-y-px border border-border bg-border">{[1, 2, 3].map((item) => <div key={item} className="h-20 animate-pulse bg-card" />)}</div>;
}

function EmptyState() {
    return <div className="empty-panel grid gap-6 text-left sm:grid-cols-[1fr_auto] sm:items-center"><div><div className="eyebrow text-accent">No lectures yet</div><h3 className="mt-3 text-3xl font-extrabold tracking-[-0.06em]">Start with the next class.</h3><p className="mt-3 max-w-lg text-sm leading-7 text-muted-foreground">Upload an audio recording and Lectify will keep you updated while it prepares the notes and study assets.</p><Link href="/teacher/upload" className="mt-6 inline-flex"><Button data-testid="empty-upload-btn" className="font-bold"><Microphone size={17} weight="bold" /> Upload lecture</Button></Link></div><div className="hidden border-l border-border pl-6 font-mono text-[0.68rem] uppercase leading-7 tracking-[0.12em] text-muted-foreground sm:block">mp3<br />wav<br />m4a<br /><span className="text-accent">≤ 200 mb</span></div></div>;
}
