import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { lectureApi, searchApi, analyticsApi, timetableApi, reviewApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { motion, useReducedMotion } from "framer-motion";
import { usePageTitle } from "@/lib/usePageTitle";
import { fmtClock, getLastSeen, getRecent, markLibrarySeen } from "@/lib/recentLectures";

const PAGE_SIZE = 24;
const SORTS = {
    newest: { label: "Newest first", fn: () => 0 }, // API order is already newest first
    oldest: { label: "Oldest first", fn: (a, b) => new Date(a.created_at) - new Date(b.created_at) },
    title: { label: "Title A–Z", fn: (a, b) => (a.title || "").localeCompare(b.title || "") },
};
const FILTER_CLASS = "field w-auto pr-8";

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

export default function StudentDashboard() {
    const { user } = useAuth();
    const reduce = useReducedMotion();
    const [lectures, setLectures] = useState([]);
    const [q, setQ] = useState("");
    const [searchResults, setSearchResults] = useState(null);
    const [searching, setSearching] = useState(false);
    const [loading, setLoading] = useState(true);
    const [analytics, setAnalytics] = useState(null);
    const [schedule, setSchedule] = useState([]);
    const [loadingSchedule, setLoadingSchedule] = useState(true);
    const [dueCount, setDueCount] = useState(0);
    usePageTitle("Library");
    const [hasMore, setHasMore] = useState(false);
    const [loadingMore, setLoadingMore] = useState(false);
    const [subject, setSubject] = useState("");
    const [sort, setSort] = useState("newest");
    // What counts as "new": published since the last time this person left the library
    const [lastSeen] = useState(() => getLastSeen(user?.id));

    useEffect(() => {
        lectureApi
            .published({ limit: PAGE_SIZE, offset: 0 })
            .then((rows) => {
                setLectures(rows);
                setHasMore(rows.length === PAGE_SIZE);
            })
            .finally(() => setLoading(false));
        analyticsApi.me().then(setAnalytics).catch(() => {});
        reviewApi.due().then((d) => setDueCount(Array.isArray(d) ? d.length : 0)).catch(() => setDueCount(0));
        timetableApi
            .getMySchedule()
            .then((slots) => setSchedule(slots || []))
            .catch(() => setSchedule([]))
            .finally(() => setLoadingSchedule(false));
    }, []);

    // Leaving the library marks everything currently listed as seen
    useEffect(() => () => markLibrarySeen(user?.id), [user?.id]);

    const loadMore = async () => {
        setLoadingMore(true);
        try {
            const rows = await lectureApi.published({ limit: PAGE_SIZE, offset: lectures.length });
            setLectures((prev) => [...prev, ...rows]);
            setHasMore(rows.length === PAGE_SIZE);
        } finally {
            setLoadingMore(false);
        }
    };

    // Debounced semantic search
    useEffect(() => {
        const term = q.trim();
        if (!term) {
            setSearchResults(null);
            return;
        }
        setSearching(true);
        const t = setTimeout(async () => {
            try {
                const r = await searchApi.search(term, 10);
                setSearchResults(r);
            } catch {
                setSearchResults([]);
            } finally {
                setSearching(false);
            }
        }, 350);
        return () => clearTimeout(t);
    }, [q]);

    const subjects = useMemo(
        () => [...new Set(lectures.map((l) => l.subject).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
        [lectures]
    );
    const browse = useMemo(
        () => lectures.filter((l) => !subject || l.subject === subject).sort(SORTS[sort].fn),
        [lectures, subject, sort]
    );

    const showList = searchResults
        ? searchResults.map((r) => ({
            id: r.lecture_id,
            title: r.title,
            subject: r.subject,
            semester: r.semester,
            snippet: r.snippet,
            score: r.score,
            created_at: null,
        }))
        : browse;

    const now = new Date();
    const hour = now.getHours();
    const part = hour < 12 ? "morning" : hour < 17 ? "afternoon" : "evening";
    const weekday = DAY_NAMES[(now.getDay() + 6) % 7];
    const firstName = (user?.name || "").trim().split(/\s+/)[0];
    const nowHM = `${String(hour).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const nowDay = (now.getDay() + 6) % 7;
    const latest = lectures[0];
    // Resume the lecture this person actually opened last (with where the audio stopped); else the newest one
    const recent = getRecent(user?.id).find((r) => lectures.some((l) => l.id === r.id));
    const resume = recent || (latest ? { id: latest.id, title: latest.title, subject: latest.subject, pos: 0 } : null);

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
                <div className="relative w-full max-w-md">
                    <Label htmlFor="student-search">Search notes</Label>
                    <Input
                        id="student-search"
                        placeholder="Dijkstra, TCP handshake"
                        value={q}
                        onChange={(e) => setQ(e.target.value)}
                        data-testid="student-search-input"
                    />
                    {searching && (
                        <span className="absolute right-3 top-9 text-sm text-muted-foreground" role="status">
                            searching
                        </span>
                    )}
                </div>
            </header>

            <div className="layout">
                <div className="col">
                    {resume && !searchResults && (
                        <motion.section
                            className="slip"
                            aria-labelledby="resume-h"
                            initial={reduce ? false : { opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                        >
                            <div className="text-overline text-muted-foreground">Pick up where you left off</div>
                            <h2 id="resume-h" className="text-2xl font-bold">{resume.title}</h2>
                            {resume.subject && (
                                <p className="mt-2 text-sm text-muted-foreground">{resume.subject}</p>
                            )}
                            <Link href={`/student/lectures/${resume.id}`} className="mt-4 inline-block">
                                <Button variant="pen" data-testid="resume-btn">
                                    {resume.pos > 0 ? `Resume at ${fmtClock(resume.pos)}` : "Open lecture"}
                                </Button>
                            </Link>
                        </motion.section>
                    )}

                    <section data-testid="published-lectures" aria-labelledby="contents-h">
                        <div className="mb-4 flex items-baseline justify-between border-b border-border pb-2">
                            <h2 id="contents-h" className="text-2xl font-bold">
                                {searchResults ? "Search results" : "Contents"}
                            </h2>
                            <span className="text-sm text-muted-foreground">
                                {showList.length} {searchResults ? "matches" : "available"}
                            </span>
                        </div>
                        {!searchResults && !loading && lectures.length > 1 && (
                            <div className="mb-4 flex flex-wrap items-center gap-3" data-testid="library-filters">
                                <label className="flex items-center gap-2 text-sm">
                                    <span className="text-muted-foreground">Subject</span>
                                    <select
                                        value={subject}
                                        onChange={(e) => setSubject(e.target.value)}
                                        className={FILTER_CLASS}
                                        data-testid="filter-subject"
                                    >
                                        <option value="">All subjects</option>
                                        {subjects.map((s) => (
                                            <option key={s} value={s}>
                                                {s}
                                            </option>
                                        ))}
                                    </select>
                                </label>
                                <label className="flex items-center gap-2 text-sm">
                                    <span className="text-muted-foreground">Sort</span>
                                    <select
                                        value={sort}
                                        onChange={(e) => setSort(e.target.value)}
                                        className={FILTER_CLASS}
                                        data-testid="filter-sort"
                                    >
                                        {Object.entries(SORTS).map(([k, v]) => (
                                            <option key={k} value={k}>
                                                {v.label}
                                            </option>
                                        ))}
                                    </select>
                                </label>
                                {subject && (
                                    <Button variant="quiet" size="sm" onClick={() => setSubject("")} data-testid="clear-filters">
                                        Clear filter
                                    </Button>
                                )}
                            </div>
                        )}
                        {loading ? (
                            <Loading />
                        ) : showList.length === 0 ? (
                            <div className="empty">
                                <h3 className="text-2xl font-bold">
                                    {searchResults ? "Nothing matches your search" : "A blank page"}
                                </h3>
                                <p className="text-sm text-muted-foreground">
                                    {searchResults
                                        ? "Try a different keyword or clear the search."
                                        : "Lectures appear here once your teacher uploads one."}
                                </p>
                                {!searchResults && <span className="hand">nothing to study yet</span>}
                            </div>
                        ) : (
                            <ol className="toc">
                                {showList.map((l) => (
                                    <li key={l.id}>
                                        <Link
                                            href={`/student/lectures/${l.id}`}
                                            data-testid={`student-lecture-card-${l.id}`}
                                            className="row"
                                        >
                                            <span className="min-w-0">
                                                <span className="t">{l.title}</span>
                                                <span className="s">
                                                    {l.snippet || [l.subject, l.semester].filter(Boolean).join(" · ")}
                                                    {l.created_at && lastSeen > 0 && new Date(l.created_at).getTime() > lastSeen && (
                                                        <span className="tag" data-testid={`new-badge-${l.id}`}>
                                                            New
                                                        </span>
                                                    )}
                                                </span>
                                            </span>
                                            <span className="aside">
                                                {l.score !== undefined ? (
                                                    <span className="date">{Math.round(l.score * 100)}% match</span>
                                                ) : l.created_at ? (
                                                    <time className="date" dateTime={l.created_at}>
                                                        {fmtDate(l.created_at)}
                                                    </time>
                                                ) : null}
                                            </span>
                                        </Link>
                                    </li>
                                ))}
                            </ol>
                        )}
                        {!searchResults && hasMore && !loading && (
                            <div className="mt-4 text-center">
                                <Button variant="quiet" onClick={loadMore} disabled={loadingMore} data-testid="library-load-more">
                                    {loadingMore ? "Loading…" : "Load more lectures"}
                                </Button>
                            </div>
                        )}
                    </section>

                    <AnalyticsRow analytics={analytics} />
                </div>

                <div className="col">
                    <section data-testid="student-timetable" aria-labelledby="planner-h">
                        {loadingSchedule ? (
                            <Loading rows={4} />
                        ) : schedule.length === 0 ? (
                            <div className="empty" data-testid="empty-timetable">
                                <h2 id="planner-h" className="text-2xl font-bold">Planner</h2>
                                <p className="text-sm text-muted-foreground">
                                    No scheduled lecture sessions for your enrolled classes yet.
                                </p>
                            </div>
                        ) : (
                            <div className="planner">
                                <header>
                                    <h2 id="planner-h" className="text-base font-bold">Planner</h2>
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
                                                data-testid={`timetable-slot-${slot.id}`}
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

                    <section aria-labelledby="due-h">
                        <h2 id="due-h" className="mb-4 text-2xl font-bold">
                            {dueCount > 0 ? "Due for review" : "All caught up"}
                        </h2>
                        {dueCount > 0 ? (
                            <>
                                <div className="deck" aria-hidden="true">
                                    <div />
                                    <div />
                                    <div>
                                        <span className="n">{dueCount}</span>
                                        <span className="text-sm text-muted-foreground">cards due</span>
                                    </div>
                                </div>
                                <Link href="/student/review" className="mt-6 inline-block">
                                    <Button variant="pen">{`Review ${dueCount} cards`}</Button>
                                </Link>
                            </>
                        ) : (
                            <p className="text-sm text-muted-foreground">
                                No cards are due. New ones appear after your next lecture is ready.
                            </p>
                        )}
                    </section>
                </div>
            </div>
        </>
    );
}

function AnalyticsRow({ analytics }) {
    if (!analytics || analytics.attempts_count === 0) return null;
    const cards = [
        { label: "Day streak", value: analytics.streak_days },
        { label: "Avg quiz score", value: `${analytics.avg_percentage}%` },
        { label: "Quizzes taken", value: analytics.attempts_count },
        { label: "Lectures studied", value: analytics.lectures_attempted },
    ];
    return (
        <section data-testid="student-analytics" aria-labelledby="progress-h">
            <h2 id="progress-h" className="mb-4 border-b border-border pb-2 text-2xl font-bold">
                Your progress
            </h2>
            <div className="week">
                {cards.map((c) => (
                    <div key={c.label} data-testid={`analytics-${c.label.toLowerCase().replace(/\s/g, "-")}`}>
                        <b>{c.value}</b>
                        <span>{c.label}</span>
                    </div>
                ))}
            </div>

            {analytics.weak_lectures?.length > 0 && (
                <div className="mt-6">
                    <div className="text-overline mb-3 text-muted-foreground">Topics needing revision</div>
                    <div className="grid gap-2">
                        {analytics.weak_lectures.map((w) => (
                            <Link
                                key={w.lecture_id}
                                href={`/student/lectures/${w.lecture_id}`}
                                className="flex min-h-11 items-center justify-between border-b border-border text-sm hover:underline"
                                data-testid={`weak-lecture-${w.lecture_id}`}
                            >
                                <span className="font-bold">{w.title}</span>
                                <span className="font-mono text-destructive">
                                    {w.avg_percentage}% · {w.attempts} attempt
                                    {w.attempts > 1 ? "s" : ""}
                                </span>
                            </Link>
                        ))}
                    </div>
                </div>
            )}
        </section>
    );
}
