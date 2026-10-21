import HierarchyTree from "@/components/HierarchyTree";
import { motion, useReducedMotion } from "framer-motion";

export default function AdminDashboard() {
    const reduce = useReducedMotion();
    return (
        <div data-testid="admin-dashboard">
            <section className="mb-10">
                <div className="text-overline mb-3 text-primary">Admin</div>
                <h1 className="text-display font-display">Academic hierarchy</h1>
                <p className="mt-3 max-w-prose text-base text-muted-foreground">
                    Manage years, branches, semesters, subjects, divisions, and classes for your institution.
                </p>
            </section>

            <motion.div
                initial={reduce ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
            >
                <HierarchyTree />
            </motion.div>
        </div>
    );
}
