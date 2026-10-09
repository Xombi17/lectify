"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { analyticsApi, lectureApi, searchApi, timetableApi } from "@/lib/api";
import { BookOpen, Calendar, Clock, Flame, MagnifyingGlass, Sparkle, Target, TrendUp, Trophy } from "@phosphor-icons/react";

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function StudentDashboard() {
    const [lectures, setLectures] = useState([]);
    const [query, setQuery] = useState("");
    const [searchResults, setSearchResults] = useState(null);
    const [searching, setSearching] = useState(false);
    const [loading, setLoading] = useState(true);
    const [analytics, setAnalytics] = useState(null);
    const [schedule, setSchedule] = useState([]);
    const [loadingSchedule, setLoadingSchedule] = useState(true);

    useEffect(() => {
        lectureApi.published().then(setLectures).finally(() => setLoading(false));
        analyticsApi.me().then(setAnalytics).catch(() => {});
        timetableApi.getMySchedule().then((items) => setSchedule(items || [])).catch(() => setSchedule([])).finally(() => setLoadingSchedule(false));
    }, []);

    useEffect(() => {
        const term = query.trim();
        if (!term) {
            setSearchResults(null);
            setSearching(false);
            return undefined;
        }
        setSearching(true);
        const timer = setTimeout(async () => {
            try {
                setSearchResults(await searchApi.search(term, 10));
            } catch {
                setSearchResults([]);
            } finally {
                setSearching(false);
            }
        }, 350);
        return () => clearTimeout(timer);
    }, [query]);

    const visibleLectures = searchResults ? searchResults.map((result) => ({ id: result.lecture_id, title: result.title, subject: result.subject, semester: result.semester, snippet: result.snippet, score: result.score })) : lectures;
    const hasProgress = analytics && analytics.attempts_count > 0;

    return (
        <div className="animate-in">
            <section className="grid gap-8 border-b border-border pb-8 lg:grid-cols-[1fr_0.42fr] lg:gap-14">
                <div>
                    <div className="eyebrow text-accent">Student library</div>
                    <h1 className="mt-3 max-w-2xl text-5xl font-extrabold leading-[0.93] tracking-[-0.07em] sm:text-6xl">Find the idea, not the timestamp.</h1>
                    <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground">Search published lectures, open a study workspace, and return to the concepts you want to keep.</p>
                    <div className="relative mt-7 max-w-2xl"><MagnifyingGlass size={18} weight="bold" className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-accent" /><Input aria-label="Search published lectures" placeholder="Search lectures or concepts" value={query} onChange={(event) => setQuery(event.target.value)} data-testid="student-search-input" className="h-12 border-border bg-card pl-11 pr-24 text-sm" />{searching && <span className="absolute right-4 top-1/2 -translate-y-1/2 font-mono text-[0.62rem] uppercase tracking-[0.1em] text-muted-foreground">searching</span>}</div>
                </div>
                <div className="self-end border-t-2 border-accent bg-card p-5 lg:mb-1"><div className="eyebrow text-muted-foreground">Your next pass</div><div className="mt-5 flex items-end justify-between gap-4"><div><div className="font-display text-4xl font-extrabold tracking-[-0.08em]">{hasProgress ? analytics.streak_days : "—"}</div><div className="mt-1 text-sm text-muted-foreground">{hasProgress ? "day study streak" : "start a study streak"}</div></div><Flame size={28} weight="duotone" className="text-accent" /></div><Link href="/student/review" className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-foreground underline decoration-accent decoration-2 underline-offset-4 hover:text-accent">Open review queue <span aria-hidden="true">→</span></Link></div>
            </section>

            <AnalyticsRow analytics={analytics} />

            <section className="mt-10" data-testid="student-timetable">
                <div className="mb-4 flex items-center justify-between border-b border-border pb-3"><div className="flex items-center gap-2"><Calendar size={18} weight="bold" className="text-accent" /><h2 className="text-lg font-extrabold tracking-[-0.04em]">Your timetable</h2></div><span className="font-mono text-[0.64rem] uppercase tracking-[0.12em] text-muted-foreground">{schedule.length} session{schedule.length === 1 ? "" : "s"}</span></div>
                {loadingSchedule ? <div className="grid gap-px border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">{[1, 2, 3, 4].map((item) => <div key={item} className="h-24 animate-pulse bg-card" />)}</div> : schedule.length === 0 ? <div className="border border-dashed border-border bg-card p-6 text-sm text-muted-foreground" data-testid="empty-timetable">No scheduled sessions for your enrolled classes yet.</div> : <div className="grid gap-px overflow-hidden border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">{[...schedule].sort((a, b) => a.day_of_week - b.day_of_week || a.start_time.localeCompare(b.start_time)).map((slot) => <div key={slot.id} data-testid={`timetable-slot-${slot.id}`} className="bg-card p-4"><div className="flex items-center justify-between gap-3"><Badge variant="secondary" className="font-semibold">{DAY_NAMES[slot.day_of_week] || `Day ${slot.day_of_week}`}</Badge>{slot.room && <span className="font-mono text-[0.65rem] text-muted-foreground">{slot.room}</span>}</div><div className="mt-4 flex items-center gap-2 text-sm font-bold"><Clock size={15} className="text-accent" weight="bold" /> {slot.start_time}–{slot.end_time}</div></div>)}</div>}
            </section>

            <section className="mt-10" data-testid="published-lectures">
                <div className="mb-4 flex items-end justify-between border-b border-border pb-3"><div><h2 className="text-lg font-extrabold tracking-[-0.04em]">{searchResults ? "Search results" : "Published lectures"}</h2><p className="mt-1 text-sm text-muted-foreground">{searchResults ? "Matches from your class library." : "Pick up from the most recent class material."}</p></div><span className="font-mono text-[0.64rem] uppercase tracking-[0.12em] text-muted-foreground">{visibleLectures.length} {searchResults ? "matches" : "available"}</span></div>
                {loading ? <div className="grid gap-px border border-border bg-border md:grid-cols-2 lg:grid-cols-3">{[1, 2, 3].map((item) => <div key={item} className="h-52 animate-pulse bg-card" />)}</div> : visibleLectures.length === 0 ? <EmptyState searched={Boolean(searchResults)} /> : <div className="grid gap-px overflow-hidden border border-border bg-border md:grid-cols-2 lg:grid-cols-3">{visibleLectures.map((lecture, index) => <motion.div key={lecture.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.035 }}><Link href={`/student/lectures/${lecture.id}`} data-testid={`student-lecture-card-${lecture.id}`} className="group block h-full bg-card p-5 transition duration-200 hover:bg-muted/50"><div className="flex items-start justify-between gap-3"><span className="flex h-10 w-10 items-center justify-center bg-muted text-accent"><BookOpen size={19} weight="bold" /></span>{lecture.score !== undefined && <span className="font-mono text-[0.62rem] text-accent">{Math.round(lecture.score * 100)}% match</span>}</div><h3 className="mt-8 font-display text-xl font-extrabold leading-tight tracking-[-0.045em]">{lecture.title}</h3>{lecture.snippet && <p className="mt-3 line-clamp-2 text-sm leading-6 text-muted-foreground">{lecture.snippet}</p>}<div className="mt-5 flex flex-wrap gap-2">{lecture.subject && <Badge variant="outline">{lecture.subject}</Badge>}{lecture.semester && <Badge variant="outline">{lecture.semester}</Badge>}</div></Link></motion.div>)}</div>}
            </section>
        </div>
    );
}

function AnalyticsRow({ analytics }) {
    if (!analytics || analytics.attempts_count === 0) return null;
    const metrics = [
        { icon: Flame, label: "Day streak", value: analytics.streak_days },
        { icon: Trophy, label: "Average score", value: `${analytics.avg_percentage}%` },
        { icon: Target, label: "Quizzes taken", value: analytics.attempts_count },
        { icon: TrendUp, label: "Lectures studied", value: analytics.lectures_attempted },
    ];
    return <section className="mt-10" data-testid="student-analytics"><div className="mb-4 flex items-center justify-between border-b border-border pb-3"><h2 className="text-lg font-extrabold tracking-[-0.04em]">Your progress</h2><Link href="/student/review" className="text-xs font-semibold text-accent hover:underline">Review cards →</Link></div><div className="grid grid-cols-2 gap-px overflow-hidden border border-border bg-border md:grid-cols-4">{metrics.map(({ icon: Icon, label, value }, index) => <div key={label} data-testid={`analytics-${label.toLowerCase().replace(/\s/g, "-")}`} className={`p-5 ${index === 0 ? "bg-accent text-accent-foreground" : "bg-card"}`}><div className={`eyebrow ${index === 0 ? "text-accent-foreground/75" : "text-muted-foreground"}`}>{label}</div><div className="mt-3 flex items-end justify-between"><strong className="font-display text-3xl font-extrabold tracking-[-0.07em]">{value}</strong><Icon size={19} weight="bold" className={index === 0 ? "text-accent-foreground" : "text-accent"} /></div></div>)}</div>{analytics.weak_lectures?.length > 0 && <div className="mt-px border border-border bg-card p-5"><div className="eyebrow text-accent">Worth another pass</div><div className="mt-3 grid gap-2">{analytics.weak_lectures.map((lecture) => <Link key={lecture.lecture_id} href={`/student/lectures/${lecture.lecture_id}`} data-testid={`weak-lecture-${lecture.lecture_id}`} className="flex items-center justify-between gap-4 border-t border-border py-3 text-sm transition hover:text-accent"><span className="font-semibold">{lecture.title}</span><span className="shrink-0 font-mono text-[0.62rem] text-destructive">{lecture.avg_percentage}% · {lecture.attempts} attempt{lecture.attempts > 1 ? "s" : ""}</span></Link>)}</div></div>}</section>;
}

function EmptyState({ searched }) {
    return <div className="empty-panel"><Sparkle size={28} className="mx-auto text-accent" weight="duotone" /><h3 className="mt-4 text-2xl font-extrabold tracking-[-0.05em]">{searched ? "No lecture matches that search" : "Nothing published yet"}</h3><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{searched ? "Try a broader term or search for a course concept." : "When your teachers publish a lecture, it will appear here with its study material."}</p></div>;
}
