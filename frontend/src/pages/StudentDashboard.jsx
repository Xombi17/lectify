import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { lectureApi } from "@/lib/api";
import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { BookOpen, MagnifyingGlass, Sparkle } from "@phosphor-icons/react";
import { motion } from "framer-motion";

const STUDENT_IMG =
    "https://images.pexels.com/photos/5553631/pexels-photo-5553631.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

export default function StudentDashboard() {
    const [lectures, setLectures] = useState([]);
    const [q, setQ] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        lectureApi
            .published()
            .then(setLectures)
            .finally(() => setLoading(false));
    }, []);

    const filtered = lectures.filter((l) =>
        [l.title, l.subject, l.semester].join(" ").toLowerCase().includes(q.toLowerCase())
    );

    return (
        <AppShell>
            {/* Hero banner */}
            <section className="mb-10 grid grid-cols-1 gap-6 lg:grid-cols-5">
                <div className="lg:col-span-3">
                    <div className="text-overline mb-3 text-primary">Your library</div>
                    <h1 className="font-display text-4xl font-black tracking-tighter sm:text-5xl">
                        Pick a lecture. <span className="bg-accent px-2">Study smart.</span>
                    </h1>
                    <p className="mt-3 max-w-xl text-base text-muted-foreground">
                        Every published lecture comes with cleaned notes, an instant quiz, and a
                        spaced-repetition flashcard deck.
                    </p>
                    <div className="relative mt-6 max-w-md">
                        <MagnifyingGlass
                            size={18}
                            weight="duotone"
                            className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                        />
                        <Input
                            placeholder="Search lectures, topics, semesters…"
                            value={q}
                            onChange={(e) => setQ(e.target.value)}
                            data-testid="student-search-input"
                            className="pl-10"
                        />
                    </div>
                </div>
                <div className="lg:col-span-2">
                    <div className="relative overflow-hidden border border-border">
                        <img src={STUDENT_IMG} alt="Student" className="h-48 w-full object-cover lg:h-56" />
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

            {/* Lecture grid */}
            <section data-testid="published-lectures">
                <div className="mb-4 flex items-center justify-between border-b border-border pb-2">
                    <h2 className="font-display text-xl font-bold tracking-tight">
                        Published lectures
                    </h2>
                    <span className="text-overline text-muted-foreground">
                        {filtered.length} available
                    </span>
                </div>

                {loading ? (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-48 animate-pulse border border-border bg-muted/40" />
                        ))}
                    </div>
                ) : filtered.length === 0 ? (
                    <div className="border-2 border-dashed border-border bg-card p-10 text-center">
                        <Sparkle size={32} weight="duotone" className="mx-auto text-muted-foreground" />
                        <h3 className="font-display mt-3 text-2xl font-bold tracking-tight">
                            Nothing published yet
                        </h3>
                        <p className="text-sm text-muted-foreground">
                            Check back when your teachers upload their first lecture.
                        </p>
                    </div>
                ) : (
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {filtered.map((l, i) => (
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
                                    <div className="mb-4 flex h-12 w-12 items-center justify-center bg-accent text-accent-foreground">
                                        <BookOpen size={22} weight="duotone" />
                                    </div>
                                    <div className="font-display text-lg font-bold leading-tight tracking-tight">
                                        {l.title}
                                    </div>
                                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                                        {l.subject && (
                                            <Badge variant="outline">{l.subject}</Badge>
                                        )}
                                        {l.semester && (
                                            <Badge variant="outline">{l.semester}</Badge>
                                        )}
                                    </div>
                                    <div className="mt-4 border-t border-border pt-3 text-overline text-muted-foreground">
                                        {new Date(l.created_at).toLocaleDateString(undefined, {
                                            month: "short",
                                            day: "numeric",
                                            year: "numeric",
                                        })}
                                    </div>
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                )}
            </section>
        </AppShell>
    );
}
