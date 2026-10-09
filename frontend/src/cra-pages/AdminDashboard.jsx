"use client";

import { Buildings } from "@phosphor-icons/react";
import { motion } from "framer-motion";
import HierarchyTree from "@/components/HierarchyTree";

export default function AdminDashboard() {
    return (
        <div className="animate-in" data-testid="admin-dashboard">
            <section className="page-intro">
                <div>
                    <div className="eyebrow text-accent">Admin workspace</div>
                    <h1>Academic setup.</h1>
                    <p>Keep the institution hierarchy clear so every lecture, timetable, and student library lands in the right class.</p>
                </div>
                <div className="hidden items-center gap-3 border border-border bg-card px-4 py-3 text-sm text-muted-foreground sm:flex"><Buildings size={19} className="text-accent" weight="bold" /><span>Institution structure</span></div>
            </section>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="surface-panel overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-muted/35 px-5 py-4"><div><div className="font-semibold">Hierarchy browser</div><div className="mt-1 text-sm text-muted-foreground">Expand a level to manage the next one.</div></div><span className="eyebrow text-muted-foreground">institution → class</span></div>
                <div className="p-4 sm:p-6"><HierarchyTree /></div>
            </motion.div>
        </div>
    );
}
