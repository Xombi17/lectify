import HierarchyTree from "@/components/HierarchyTree";
import { Buildings } from "@phosphor-icons/react";
import { motion } from "framer-motion";

export default function AdminDashboard() {
    return (
            <div data-testid="admin-dashboard">
                <section className="mb-10">
                    <div className="text-overline mb-3 text-primary">Admin dashboard</div>
                    <h1 className="font-display text-4xl font-black tracking-tighter sm:text-5xl">
                        Academic hierarchy.
                    </h1>
                    <p className="mt-3 max-w-xl text-base text-muted-foreground">
                        Manage institutions, years, branches, semesters, subjects, divisions, and classes.
                    </p>
                </section>

                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                >
                    <HierarchyTree />
                </motion.div>
            </div>
    );
}