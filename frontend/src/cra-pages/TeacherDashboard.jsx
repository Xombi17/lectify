import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { academicApi, lectureApi, timetableApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePageTitle } from "@/lib/usePageTitle";
import StatusStamp from "@/components/StatusStamp";
import { UploadSimple } from "@/components/icons";
import { motion, useReducedMotion } from "framer-motion";

const PAGE_SIZE = 20;

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const fmtDate = (d) =>
    new Date(d).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

function Loading({ rows = 3 }) {
    return (
        <div aria-busy="true" aria-label="Loading" className="grid gap-4">
            {Array.from({ length: rows }, (_, i) => (
                <span key={i} className="sk" />
            ))}
        </div>
    );
}

export default function TeacherDashboard() {
    const { user } = useAuth();
    const reduce = useReducedMotion();
    const [lectures, setLectures] = useState([]);
    const [loading, setLoading] = useState(true);
    const [schedule, setSchedule] = useState([]);
    const [assignedClasses, setAssignedClasses] = useState([]);
    usePageTitle("Dashboard");
    const [q, setQ] = useState("");
    const [hasMore, setHasMore] = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);
    // The 8 s status poll re-fetches everything loaded so far, so "Load more" is never wiped by a refresh
    const pagesRef = useRef(1);

    const load = async () => {
        try {
            const size = pagesRef.current * PAGE_SIZE;
            const rows = await lectureApi.mine({ limit: size, offset: 0 });
            setLectures(rows);
            setHasMore(rows.length === size);
        } finally {
            setLoading(false);
        }
    };

    const loadMore = () => {
        pagesRef.current += 1;
        setLoadingMore(true);
        load().finally(() => setLoadingMore(false));
    };

    const needle = q.trim().toLowerCase();
    const visible = needle
        ? lectures.filter((l) =>
              [l.title, l.subject, l.semester].filter(Boolean).some((v) => v.toLowerCase().includes(needle))
          )
        : lectures;

    useEffect(() => {
        load();
        timetableApi.getMySchedule().then((s) => setSchedule(s || [])).catch(() => setSchedule([]));
        academicApi.getMyAssignedClasses().then((c) => setAssignedClasses(c || [])).catch(() => setAssignedClasses([]));
        const t = setInterval(load, 8000); // poll while processing
        return () => clearInterval(t);
    }, []);

    const stats = {
        total: lectures.length,
        ready: lectures.filter((l) => l.status === "ready").length,
        processing: lectures.filter((l) => l.status === "processing" || l.status === "uploaded").length,
        published: lectures.filter((l) => l.published).length,
    };

    const now = new Date();
    const hour = now.getHours();
    const part = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";
    const weekday = DAY_NAMES[(now.getDay() + 6) % 7];
    const firstName = (user?.name || "").trim().split(/\s+/)[0];
    const nowHM = `${String(hour).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const nowDay = (now.getDay() + 6) % 7;

    return (
        <>
            <header className="head">
                <div>
                    <div className="hand text-primary" suppressHydrationWarning>
                        {weekday} {part}
                    </div>
                    <h1 className="text-display" suppressHydrationWarning>
                        Good {part}
                        {firstName ? `, ${firstName}` : ""}
                    </h1>
                </div>
                <Link href="/teacher/upload">
                    <Button variant="pen" size="lg" data-testid="upload-lecture-btn">
                        <UploadSimple size="1em" aria-hidden="true" weight="bold" />
                        Upload lecture
                    </Button>
                </Link>
            </header>

            <section className="mb-10" aria-label="Lecture counts">
                <div className="week">
                    {[
                        { label: "Total lectures", value: stats.total },
                        { label: "Ready to publish", value: stats.ready },
                        { label: "In processing", value: stats.processing },
                        { label: "Published", value: stats.published },
                    ].map((s) => (
                        <div key={s.label} data-testid={`stat-${s.label.toLowerCase().replace(/\s/g, "-")}`}>
                            <b className="font-mono">{s.value}</b>
                            <span className="text-sm">{s.label}</span>
                        </div>
                    ))}
                </div>
            </section>

            <div className="layout">
                <div className="col">
                    <section data-testid="teacher-classes" aria-labelledby="classes-h">
                        <div className="mb-4 flex items-baseline justify-between border-b border-border pb-2">
                            <h2 id="classes-h" className="text-2xl font-bold">My classes</h2>
                            <span className="text-sm text-muted-foreground">{assignedClasses.length} assigned</span>
                        </div>

                        {assignedClasses.length === 0 ? (
                            <div className="empty" data-testid="empty-assigned-classes">
                                <p className="text-sm text-muted-foreground">
                                    No assigned classes found. Contact an administrator to assign classes before uploading lectures.
                                </p>
                            </div>
                        ) : (
                            <div className="grid gap-4 sm:grid-cols-2">
                                {assignedClasses.map((c, idx) => (
                                    <motion.div
                                        key={c.class_id}
                                        initial={reduce ? false : { opacity: 0, y: 8 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.04 }}
                                        data-testid={`teacher-class-card-${c.class_id}`}
                                        className="slip flex flex-col"
                                    >
                                        <h3 className="text-xl">{c.subject_name || "Untitled subject"}</h3>
                                        <p className="mt-2 text-sm text-muted-foreground">
                                            {[c.division_name, c.semester_label].filter(Boolean).join(" · ")}
                                        </p>
                                        <Link href={`/teacher/upload?class_id=${c.class_id}`} className="mt-auto pt-5">
                                            <Button
                                                className="w-full"
                                                data-testid={`upload-to-class-${c.class_id}`}
                                            >
                                                <UploadSimple size="1em" aria-hidden="true" weight="bold" />
                                                Upload lecture
                                            </Button>
                                        </Link>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </section>

                    <section data-testid="lectures-list" aria-labelledby="recent-h">
                        <div className="mb-4 flex items-baseline justify-between border-b border-border pb-2">
                            <h2 id="recent-h" className="text-2xl font-bold">Recent lectures</h2>
                            <span className="text-sm text-muted-foreground">Auto-refreshing</span>
                        </div>

                        {!loading && lectures.length > 0 && (
                            <Input
                                value={q}
                                onChange={(e) => setQ(e.target.value)}
                                placeholder="Search your lectures"
                                aria-label="Search your lectures"
                                className="mb-4 max-w-md"
                                data-testid="teacher-search-input"
                            />
                        )}

                        {loading ? (
                            <Loading />
                        ) : lectures.length === 0 ? (
                            <div className="empty">
                                <h3 className="text-2xl font-bold">A blank page</h3>
                                <p className="text-sm text-muted-foreground">
                                    Upload your first lecture and it shows up here once it is ready.
                                </p>
                                <span className="hand">nothing to study yet</span>
                                <Link href="/teacher/upload" className="mt-2 inline-block">
                                    <Button variant="pen" data-testid="empty-upload-btn">
                                        <UploadSimple size="1em" aria-hidden="true" weight="bold" />
                                        Upload lecture
                                    </Button>
                                </Link>
                            </div>
                        ) : visible.length === 0 ? (
                            <p className="py-6 text-sm text-muted-foreground" data-testid="teacher-no-match">
                                No lectures match &ldquo;{q}&rdquo;.
                            </p>
                        ) : (
                            <ol className="toc">
                                {visible.map((l) => (
                                    <li key={l.id}>
                                        <Link
                                            href={`/teacher/lectures/${l.id}`}
                                            data-testid={`lecture-row-${l.id}`}
                                            className="row"
                                        >
                                            <span className="min-w-0">
                                                <span className="t">{l.title}</span>
                                                <span className="s">
                                                    {[l.subject, l.semester].filter(Boolean).join(" · ")}
                                                    {l.published && <span className="tag">Published</span>}
                                                </span>
                                            </span>
                                            <span className="aside">
                                                <StatusStamp status={l.status} />
                                                {l.created_at && (
                                                    <time className="date" dateTime={l.created_at}>
                                                        {fmtDate(l.created_at)}
                                                    </time>
                                                )}
                                            </span>
                                        </Link>
                                    </li>
                                ))}
                            </ol>
                        )}
                        {hasMore && !loading && (
                            <div className="mt-4 text-center">
                                <Button variant="quiet" onClick={loadMore} disabled={loadingMore} data-testid="teacher-load-more">
                                    {loadingMore ? "Loading…" : "Load more lectures"}
                                </Button>
                            </div>
                        )}
                    </section>
                </div>

                <div className="col">
                    <section data-testid="teacher-schedule" aria-labelledby="planner-h">
                        {schedule.length === 0 ? (
                            <div className="empty text-left" data-testid="empty-teacher-schedule">
                                <h2 id="planner-h" className="text-xl">Weekly teaching schedule</h2>
                                <p className="mt-2 text-sm text-muted-foreground">
                                    No timetable slots yet. Your administrator adds them per class; they show up here with
                                    the session that is on now highlighted.
                                </p>
                            </div>
                        ) : (
                            <div className="planner">
                                <header>
                                    <h2 id="planner-h" className="text-base font-bold">Weekly teaching schedule</h2>
                                    <span className="text-sm">
                                        {schedule.length} session{schedule.length === 1 ? "" : "s"}
                                    </span>
                                </header>
                                {[...schedule]
                                    .sort((a, b) => a.day_of_week - b.day_of_week || a.start_time.localeCompare(b.start_time))
                                    .map((slot) => {
                                        const isNow =
                                            slot.day_of_week === nowDay &&
                                            slot.start_time <= nowHM &&
                                            nowHM < slot.end_time;
                                        return (
                                            <div
                                                key={slot.id}
                                                data-testid={`schedule-slot-${slot.id}`}
                                                className={`pl ${isNow ? "now bg-accent text-accent-foreground" : ""}`}
                                                aria-current={isNow ? "time" : undefined}
                                            >
                                                <time>{slot.start_time}</time>
                                                <span>
                                                    <b>{DAY_NAMES[slot.day_of_week] || `Day ${slot.day_of_week}`}</b>
                                                    <small className="font-mono">
                                                        {slot.start_time} - {slot.end_time}
                                                    </small>
                                                </span>
                                                {slot.room && <small>{slot.room}</small>}
                                            </div>
                                        );
                                    })}
                            </div>
                        )}
                    </section>
                </div>
            </div>
        </>
    );
}
