import { useEffect, useState } from "react";
import Image from "next/image";
import { Link } from "react-router-dom";
import { lectureApi, searchApi, analyticsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
    BookOpen,
    MagnifyingGlass,
    Sparkle,
    Flame,
    Target,
    TrendUp,
    Trophy,
} from "@phosphor-icons/react";
import { motion } from "framer-motion";

const STUDENT_IMG =
    "https://images.pexels.com/photos/5553631/pexels-photo-5553631.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

export default function StudentDashboard() {
    const [lectures, setLectures] = useState([]);
    const [q, setQ] = useState("");
    const [searchResults, setSearchResults] = useState(null);
    const [searching, setSearching] = useState(false);
    const [loading, setLoading] = useState(true);
    const [analytics, setAnalytics] = useState(null);

    useEffect(() => {
        lectureApi
            .published()
            .then(setLectures)
            .finally(() => setLoading(false));
        analyticsApi.me().then(setAnalytics).catch(() => {});
    }, []);

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
        : lectures;

    return (
        {/* Hero banner */}
            <section className="mb-10 grid grid-cols-1 gap-6 lg:grid-cols-5">
                <div className="lg:col-span-3">
                    <div className="text-overline mb-3 text-primary">Your library</div>
                    <h1 className="font-display text-4xl font-black tracking-tighter sm:text-5xl">
                        Pick a lecture. <span className="bg-accent px-2">Study smart.</span>
                    </h1>
                    <p className="mt-3 max-w-xl text-base text-muted-foreground">
                        Every published lecture comes with cleaned notes, an instant quiz, and a
                        flashcard deck. Ask the AI any doubt — answers stay grounded in your
                        teacher&apos;s words.
                    </p>
                    <div className="relative mt-6 max-w-md">
                        <MagnifyingGlass
                            size={18}
                            weight="duotone"
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                        />
                        <Input
                            placeholder="Search semantically: 'Dijkstra', 'TCP handshake'…"
                            value={q}
                            onChange={(e) => setQ(e.target.value)}
                            data-testid="student-search-input"
                            className="pl-10"
                        />
                        {searching && (
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                                searching…
                            </span>
                        )}
                    </div>
                </div>
                <div className="lg:col-span-2">
                    <div className="relative overflow-hidden border border-border">
                        <Image
                            src={STUDENT_IMG}
                            alt="Student studying"
                            width={940}
                            height={650}
                            className="h-48 w-full object-cover lg:h-56"
                            priority
                        />
                        <div className="absolute inset-0 bg-primary/40" />
                        <div className="absolute bottom-4 left-4 right-4 text-white">
                            <div className="text-overline text-accent">Pro tip</div>
                            <div className="font-display text-lg font-bold leading-tight">
                                Quiz yourself within 24 hours of every lecture for 2× retention.
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Analytics row */}
            <AnalyticsRow analytics={analytics} />

            {/* Lecture grid */}
            <section data-testid="published-lectures">
                <div className="mb-4 flex items-center justify-between border-b border-border pb-2">
                    <h2 className="font-display text-xl font-bold tracking-tight">
                        {searchResults ? "Search results" : "Published lectures"}
                    </h2>
                    <span className="text-overline text-muted-foreground">
                        {showList.length} {searchResults ? "matches" : "available"}
                    </span>
                </div>

                {loading ? (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {[1, 2, 3].map((i) => (
                            <div
                                key={i}
                                className="h-48 animate-pulse border border-border bg-muted/40"
                            />
                        ))}
                    </div>
                ) : showList.length === 0 ? (
                    <div className="border-2 border-dashed border-border bg-card p-10 text-center">
                        <Sparkle size={32} weight="duotone" className="mx-auto text-muted-foreground" />
                        <h3 className="font-display mt-3 text-2xl font-bold tracking-tight">
                            {searchResults ? "Nothing matches your search" : "Nothing published yet"}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                            {searchResults
                                ? "Try a different keyword or clear the search."
                                : "Check back when your teachers upload their first lecture."}
                        </p>
                    </div>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {showList.map((l, i) => (
                            <motion.div
                                key={l.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.04 }}
                            >
                                <Link
                                    to={`/student/lectures/${l.id}`}
                                    data-testid={`student-lecture-card-${l.id}`}
                                    className="group block h-full border border-border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-sm"
                                >
                                    <div className="mb-4 flex items-center justify-between">
                                        <div className="flex h-12 w-12 items-center justify-center bg-accent text-accent-foreground">
                                            <BookOpen size={22} weight="duotone" />
                                        </div>
                                        {l.score !== undefined && (
                                            <span className="text-overline text-primary">
                                                {Math.round(l.score * 100)}% match
                                            </span>
                                        )}
                                    </div>
                                    <div className="font-display text-lg font-bold leading-tight tracking-tight">
                                        {l.title}
                                    </div>
                                    {l.snippet && (
                                        <p className="mt-2 line-clamp-2 text-sm text-muted-foreground">
                                            {l.snippet}
                                        </p>
                                    )}
                                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                                        {l.subject && <Badge variant="outline">{l.subject}</Badge>}
                                        {l.semester && <Badge variant="outline">{l.semester}</Badge>}
                                    </div>
                                    {l.created_at && (
                                        <div className="mt-4 border-t border-border pt-3 text-overline text-muted-foreground">
                                            {new Date(l.created_at).toLocaleDateString(undefined, {
                                                month: "short",
                                                day: "numeric",
                                                year: "numeric",
                                            })}
                                        </div>
                                    )}
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                )}
            </section>
    );
}

function AnalyticsRow({ analytics }) {
    if (!analytics || analytics.attempts_count === 0) return null;
    const cards = [
        { icon: Flame, label: "Day streak", value: analytics.streak_days },
        { icon: Trophy, label: "Avg quiz score", value: `${analytics.avg_percentage}%` },
        { icon: Target, label: "Quizzes taken", value: analytics.attempts_count },
        { icon: TrendUp, label: "Lectures studied", value: analytics.lectures_attempted },
    ];
    return (
        <section className="mb-10" data-testid="student-analytics">
            <div className="mb-4 border-b border-border pb-2">
                <h2 className="font-display text-xl font-bold tracking-tight">Your progress</h2>
            </div>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {cards.map((c, i) => {
                    const Icon = c.icon;
                    return (
                        <div
                            key={i}
                            data-testid={`analytics-${c.label.toLowerCase().replace(/\s/g, "-")}`}
                            className={`border border-border p-5 ${
                                i === 0 ? "bg-primary text-primary-foreground" : "bg-card"
                            }`}
                        >
                            <div
                                className={`text-overline ${
                                    i === 0 ? "text-accent" : "text-muted-foreground"
                                }`}
                            >
                                {c.label}
                            </div>
                            <div className="mt-1 flex items-end justify-between">
                                <div className="font-display text-3xl font-black tracking-tighter">
                                    {c.value}
                                </div>
                                <Icon size={20} weight="duotone" className={i === 0 ? "text-accent" : "text-primary"} />
                            </div>
                        </div>
                    );
                })}
            </div>

            {analytics.weak_lectures?.length > 0 && (
                <div className="mt-4 border border-border bg-card p-5">
                    <div className="text-overline mb-3 text-primary">Topics needing revision</div>
                    <div className="grid gap-2">
                        {analytics.weak_lectures.map((w) => (
                            <Link
                                key={w.lecture_id}
                                to={`/student/lectures/${w.lecture_id}`}
                                className="flex items-center justify-between border-b border-border pb-2 text-sm transition-colors hover:text-primary"
                                data-testid={`weak-lecture-${w.lecture_id}`}
                            >
                                <span className="font-display font-bold">{w.title}</span>
                                <span className="text-overline text-destructive">
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
