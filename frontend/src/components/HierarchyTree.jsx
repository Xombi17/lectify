import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
    CaretRight,
    CaretLeft,
    Buildings,
    GitBranch,
    GraduationCap,
    CalendarBlank,
    BookBookmark,
    UsersThree,
    ChalkboardTeacher,
    Plus,
    PencilSimple,
    Trash,
    CheckCircle,
    Circle,
    QrCode,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { adminApi } from "@/lib/api";
import { toast } from "sonner";
import CreateEntityDialog from "@/components/CreateEntityDialog";
import TeacherAssignmentPanel from "@/components/TeacherAssignmentPanel";
import QRCodeCard from "@/components/QRCodeCard";
import EnrollmentTable from "@/components/EnrollmentTable";

// Level config: icon, label, and which child groups each level has.
// The navigator shows one level at a time — select a card to drill in,
// use the breadcrumb to go back. No hover-only actions, no dead ends.
const LEVEL_CONFIG = {
    institution: {
        icon: Buildings,
        label: "Institution",
        childGroups: [
            {
                key: "years",
                label: "Years",
                icon: CalendarBlank,
                listFn: (id) => adminApi.listInstitutionYears(id),
                childType: "year",
                hint: "Academic years, e.g. First Year, Second Year",
            },
            {
                key: "branches",
                label: "Departments",
                icon: GitBranch,
                listFn: (id) => adminApi.listInstitutionBranches(id),
                childType: "branch",
                hint: "Departments, e.g. Computer, CSE, ECS, Mechanical",
            },
            {
                key: "batches",
                label: "Batches",
                icon: GraduationCap,
                listFn: (id) => adminApi.listInstitutionBatches(id),
                childType: "batch",
                hint: "Graduating cohorts — divisions can differ per batch",
            },
        ],
    },
    year: {
        icon: CalendarBlank,
        label: "Year",
        childGroups: [
            {
                key: "semesters",
                label: "Semesters",
                icon: CalendarBlank,
                listFn: (id) => adminApi.listYearSemesters(id),
                childType: "semester",
                hint: "Terms inside this year, e.g. Sem 1, Sem 2",
            },
        ],
    },
    branch: {
        icon: GitBranch,
        label: "Department",
        childGroups: [],
    },
    batch: {
        icon: GraduationCap,
        label: "Batch",
        childGroups: [
            {
                key: "divisions",
                label: "Divisions",
                icon: UsersThree,
                listFn: (id) => adminApi.listBatchDivisions(id),
                childType: "division",
                hint: "This cohort's divisions across all departments",
            },
        ],
    },
    semester: {
        icon: CalendarBlank,
        label: "Semester",
        childGroups: [
            {
                key: "subjects",
                label: "Subjects",
                icon: BookBookmark,
                listFn: (id) => adminApi.listSemesterSubjects(id),
                childType: "subject",
                hint: "Courses taught this term",
            },
            {
                key: "divisions",
                label: "Divisions",
                icon: UsersThree,
                listFn: (id) => adminApi.listSemesterDivisions(id),
                childType: "division",
                hint: "Student batches, e.g. Div A, Div B",
            },
        ],
    },
    subject: {
        icon: BookBookmark,
        label: "Subject",
        childGroups: [],
    },
    division: {
        icon: UsersThree,
        label: "Division",
        childGroups: [
            {
                key: "classes",
                label: "Classes",
                icon: ChalkboardTeacher,
                listFn: (id) => adminApi.listDivisionClasses(id),
                childType: "class",
                hint: "A class links one subject to one division",
            },
        ],
    },
    class: {
        icon: ChalkboardTeacher,
        label: "Class",
        childGroups: [],
    },
};

const DELETE_FNS = {
    institution: adminApi.deleteInstitution,
    year: adminApi.deleteYear,
    branch: adminApi.deleteBranch,
    batch: adminApi.deleteBatch,
    semester: adminApi.deleteSemester,
    subject: adminApi.deleteSubject,
    division: adminApi.deleteDivision,
    class: adminApi.deleteClass,
};

const UPDATE_FNS = {
    institution: (id, d, name) => adminApi.updateInstitution(id, { name, code: d.code, address: d.address }),
    year: (id, d, name) => adminApi.updateYear(id, { name, number: d.number, institution_id: d.institution_id }),
    branch: (id, d, name) => adminApi.updateBranch(id, { name, code: d.code, institution_id: d.institution_id }),
    batch: (id, d, name) => adminApi.updateBatch(id, { name, admission_year: d.admission_year, graduating_year: d.graduating_year, institution_id: d.institution_id }),
    semester: (id, d, name) => adminApi.updateSemester(id, { label: name, number: d.number, year_id: d.year_id }),
    subject: (id, d, name) => adminApi.updateSubject(id, { name, code: d.code, semester_id: d.semester_id, credits: d.credits }),
    division: (id, d, name) => adminApi.updateDivision(id, { name, semester_id: d.semester_id ?? null, branch_id: d.branch_id ?? null, batch_id: d.batch_id ?? null, capacity: d.capacity ?? null }),
    class: (id, d, name) => adminApi.updateClass(id, { name, division_id: d.division_id, subject_id: d.subject_id }),
};

function displayName(type, data) {
    if (!data) return "";
    if (data.name) return data.name;
    if (data.label) return data.label;
    if (data.code) return data.code;
    if (type === "year" && data.number != null) return `Year ${data.number}`;
    if (type === "semester" && data.number != null) return `Semester ${data.number}`;
    if (type === "batch" && data.graduating_year != null) return data.name || `Batch of ${data.graduating_year}`;
    if (type === "class") return `Class ${String(data.id).slice(0, 8)}`;
    return String(data.id).slice(0, 8);
}

function displayMeta(type, data) {
    if (!data) return "";
    if (type === "institution" && data.code) return data.code;
    if (type === "branch" && data.code) return data.code;
    if (type === "subject" && data.code) return `${data.code}${data.credits ? ` · ${data.credits} credits` : ""}`;
    if (type === "division" && data.capacity) return `Capacity ${data.capacity}`;
    if (type === "semester" && data.label && data.number != null) return data.label;
    if (type === "batch" && data.admission_year != null && data.graduating_year != null)
        return `Admitted ${data.admission_year} · Graduating ${data.graduating_year}`;
    if (type === "year" && data.name && data.number != null) return data.name;
    return "";
}

// Setup checklist — the guided path from empty database to first
// enrolments. Each step shows its state and jumps straight to the
// place where the work happens. Recognition over recall.
// Single-institution app: the college itself is fixed, so the guide
// starts at the academic year.
const CHECKLIST = [
    { key: "batch", label: "Create graduating batches", detail: "e.g. Batch of 2028, Batch of 2029" },
    { key: "year", label: "Add an academic year", detail: "e.g. First Year" },
    { key: "semester", label: "Add a semester", detail: "e.g. Sem 1 inside the year" },
    { key: "offering", label: "Add a subject and a division", detail: "What is taught, and to which batch" },
    { key: "class", label: "Create a class, assign a teacher", detail: "Link subject + division, then share the QR" },
];

export default function HierarchyTree() {
    const [institutions, setInstitutions] = useState([]);
    const [loadingRoot, setLoadingRoot] = useState(true);
    const [stats, setStats] = useState(null);
    // Path of selected nodes, e.g. [{type:'institution',data},{type:'year',data}]
    const [path, setPath] = useState([]);
    // Children cache: `${type}:${id}` -> { groupKey: items[] }
    const [kids, setKids] = useState({});
    const [loadingKids, setLoadingKids] = useState(false);
    // Create dialog state
    const [createType, setCreateType] = useState(null);
    const [createParentId, setCreateParentId] = useState(null);
    const [createOptions, setCreateOptions] = useState({});
    const [createInitial, setCreateInitial] = useState({});
    const [rev, setRev] = useState(0);
    // Rename state: `${type}:${id}` -> draft name
    const [renaming, setRenaming] = useState(null);
    const [renameValue, setRenameValue] = useState("");
    // Class detail: teacher dialog
    const [showTeachers, setShowTeachers] = useState(false);
    // Checklist jump in progress
    const [jumping, setJumping] = useState(false);

    const loadRoot = useCallback(async () => {
        setLoadingRoot(true);
        try {
            const [insts, years, semesters, subjects, divisions, classes, branches, batches] = await Promise.all([
                adminApi.listInstitutions().catch(() => []),
                adminApi.listYears().catch(() => []),
                adminApi.listSemesters().catch(() => []),
                adminApi.listSubjects().catch(() => []),
                adminApi.listDivisions().catch(() => []),
                adminApi.listClasses().catch(() => []),
                adminApi.listBranches().catch(() => []),
                adminApi.listBatches().catch(() => []),
            ]);
            setInstitutions(insts || []);
            setStats({
                institution: (insts || []).length,
                year: (years || []).length,
                semester: (semesters || []).length,
                subject: (subjects || []).length,
                division: (divisions || []).length,
                class: (classes || []).length,
                branch: (branches || []).length,
                batch: (batches || []).length,
                _years: years || [],
                _semesters: semesters || [],
                _divisions: divisions || [],
            });
        } catch {
            toast.error("Failed to load hierarchy");
        } finally {
            setLoadingRoot(false);
        }
    }, []);

    useEffect(() => {
        loadRoot();
    }, [loadRoot, rev]);

    const cacheKey = (type, id) => `${type}:${id}`;

    const loadChildren = useCallback(async (type, id) => {
        const groups = LEVEL_CONFIG[type]?.childGroups || [];
        if (groups.length === 0) return {};
        setLoadingKids(true);
        try {
            const results = {};
            for (const g of groups) {
                results[g.key] = (await g.listFn(id).catch(() => [])) || [];
            }
            setKids((prev) => ({ ...prev, [cacheKey(type, id)]: results }));
            return results;
        } finally {
            setLoadingKids(false);
        }
    }, []);

    const refresh = useCallback(() => {
        setKids({});
        setRev((r) => r + 1);
    }, []);

    // Single-institution app: pin the navigator to the college itself.
    // The institution level is skipped — the admin starts at its years.
    useEffect(() => {
        if (!loadingRoot && institutions.length > 0 && path.length === 0) {
            const inst = institutions[0];
            setPath([{ type: "institution", data: inst }]);
            loadChildren("institution", inst.id);
        }
    }, [loadingRoot, institutions, path.length, loadChildren]);

    const current = path[path.length - 1] || null;

    // Drill into a child node
    const openNode = (type, data) => {
        const next = [...path, { type, data }];
        setPath(next);
        const key = cacheKey(type, data.id);
        if (!kids[key] && (LEVEL_CONFIG[type]?.childGroups?.length || 0) > 0) {
            loadChildren(type, data.id);
        }
    };

    const goToCrumb = (index) => {
        // The college itself is the root — the path never goes below it
        setPath(path.slice(0, Math.max(index + 1, 1)));
    };

    const openCreate = async (type, parentId, { initial = {}, options = {} } = {}) => {
        // Classes need a subject picker: the division's department when known
        // (cohort divisions carry branch_id), else the current semester, else all.
        // They also pin the teaching period: the division's batch current term.
        if (type === "class") {
            const divisionNode = current?.type === "division" ? current : null;
            const semesterNode = [...path].reverse().find((p) => p.type === "semester");
            try {
                let subjects = [];
                if (divisionNode?.data?.branch_id) {
                    subjects = (await adminApi.listBranchSubjects(divisionNode.data.branch_id).catch(() => [])) || [];
                } else if (semesterNode) {
                    subjects = (await adminApi.listSemesterSubjects(semesterNode.data.id).catch(() => [])) || [];
                } else {
                    subjects = (await adminApi.listSubjects().catch(() => [])) || [];
                }
                options = {
                    ...options,
                    subject_id: subjects.map((s) => ({
                        value: s.id,
                        label: s.name ? `${s.name}${s.code ? ` (${s.code})` : ""}` : s.id,
                    })),
                };
                if (divisionNode?.data?.batch_id) {
                    const rows = (await adminApi.listBatchSemesters(divisionNode.data.batch_id).catch(() => [])) || [];
                    const semesters = (await adminApi.listSemesters().catch(() => [])) || [];
                    const labelOf = (sid) => {
                        const s = semesters.find((x) => x.id === sid);
                        return s ? (s.label || `Semester ${s.number}`) : sid.slice(0, 8);
                    };
                    options = {
                        ...options,
                        batch_semester_id: rows.map((r) => ({
                            value: r.id,
                            label: `${labelOf(r.semester_id)} · ${r.academic_year}`,
                        })),
                    };
                    const now = new Date().toISOString().slice(0, 10);
                    const currentRow = rows.find((r) => r.starts_on <= now && r.ends_on >= now);
                    if (currentRow) initial = { ...initial, batch_semester_id: currentRow.id };
                }
            } catch {
                options = { ...options };
            }
        }
        // Subjects pick their department from a dropdown (divisions already
        // get branch/batch/semester dropdowns from the block below).
        if (type === "subject") {
            try {
                const branches = (await adminApi.listBranches().catch(() => [])) || [];
                if (!options.branch_id) {
                    options = {
                        ...options,
                        branch_id: branches.map((b) => ({
                            value: b.id,
                            label: b.name ? `${b.name} (${b.code})` : b.code,
                        })),
                    };
                }
            } catch {
                options = { ...options };
            }
        }
        // Divisions are placed by department × batch (or legacy semester).
        // Offer dropdowns for all three so nothing has to be pasted as an ID.
        if (type === "division") {
            try {
                const [branches, batches, semesters] = await Promise.all([
                    adminApi.listBranches().catch(() => []),
                    adminApi.listBatches().catch(() => []),
                    adminApi.listSemesters().catch(() => []),
                ]);
                const opt = (items, fmt) => (items || []).map((x) => ({ value: x.id, label: fmt(x) }));
                options = {
                    ...options,
                    branch_id: opt(branches, (b) => (b.name ? `${b.name} (${b.code})` : b.code)),
                    batch_id: opt(batches, (b) => b.name || `Batch of ${b.graduating_year}`),
                    semester_id: opt(semesters, (s) => s.label || `Semester ${s.number}`),
                };
            } catch {
                options = { ...options };
            }
        }
        setCreateParentId(parentId);
        setCreateOptions(options);
        setCreateInitial(initial);
        setCreateType(type);
    };

    const handleCreateSuccess = async () => {
        setCreateType(null);
        // Reload children of the parent level + global stats
        if (current) await loadChildren(current.type, current.data.id);
        refresh();
    };

    const handleDelete = async (type, data) => {
        if (!window.confirm(`Delete "${displayName(type, data)}"? This cannot be undone.`)) return;
        try {
            await DELETE_FNS[type](data.id);
            toast.success(`${LEVEL_CONFIG[type].label} deleted`);
            // If we deleted the node we're viewing, step back up
            if (current && current.data.id === data.id) {
                setPath(path.slice(0, -1));
            }
            if (current) await loadChildren(current.type, current.data.id).catch(() => {});
            refresh();
        } catch {
            toast.error(`Failed to delete ${LEVEL_CONFIG[type].label}`);
        }
    };

    const startRename = (type, data) => {
        setRenaming(cacheKey(type, data.id));
        setRenameValue(displayName(type, data));
    };

    const saveRename = async (type, data) => {
        if (!renameValue.trim()) {
            setRenaming(null);
            return;
        }
        try {
            const updated = await UPDATE_FNS[type](data.id, data, renameValue.trim());
            toast.success(`${LEVEL_CONFIG[type].label} renamed`);
            setRenaming(null);
            // Patch the renamed node wherever it appears (path + lists)
            const patch = (d) => (d && d.id === data.id ? { ...d, ...updated } : d);
            setPath((p) => p.map((n) => (n.data.id === data.id ? { ...n, data: patch(n.data) } : n)));
            setInstitutions((list) => list.map(patch));
            setKids((prev) => {
                const next = {};
                for (const [k, groups] of Object.entries(prev)) {
                    next[k] = {};
                    for (const [gk, items] of Object.entries(groups)) {
                        next[k][gk] = (items || []).map(patch);
                    }
                }
                return next;
            });
        } catch {
            toast.error(`Failed to rename ${LEVEL_CONFIG[type].label}`);
        }
    };

    // Checklist: jump to the right context and open the right dialog.
    // The institution is fixed (single-college app) — always the first one.
    const jumpToStep = async (step) => {
        if (!stats || jumping || institutions.length === 0) return;
        setJumping(true);
        try {
            const inst = institutions[0];
            const pickYear = async (yearId) =>
                (await adminApi.getYear(yearId).catch(() => null))
                || stats._years.find((x) => x.id === yearId);
            if (step === "batch") {
                setCreateParentId(inst.id);
                setCreateOptions({});
                setCreateInitial({});
                setCreateType("batch");
                return;
            }
            if (step === "year") {
                const y = stats._years[0];
                if (!y) {
                    setPath([{ type: "institution", data: inst }]);
                    await loadChildren("institution", inst.id);
                    setCreateParentId(inst.id);
                    setCreateOptions({});
                    setCreateType("year");
                    return;
                }
                setPath([{ type: "institution", data: inst }, { type: "year", data: y }]);
                return;
            }
            if (step === "semester") {
                const s = stats._semesters[0];
                if (!s) return jumpToStep("year");
                const y = await pickYear(s.year_id);
                const built = [
                    { type: "institution", data: inst },
                    y && { type: "year", data: y },
                ].filter(Boolean);
                setPath(built);
                if (y) {
                    await loadChildren("year", y.id);
                    setCreateParentId(y.id);
                    setCreateOptions({});
                    setCreateType("semester");
                }
                return;
            }
            if (step === "offering") {
                const s = stats._semesters[0];
                if (!s) return jumpToStep("semester");
                const y = await pickYear(s.year_id);
                setPath(
                    [
                        { type: "institution", data: inst },
                        y && { type: "year", data: y },
                        { type: "semester", data: s },
                    ].filter(Boolean)
                );
                await loadChildren("semester", s.id);
                return;
            }
            if (step === "class") {
                const d = stats._divisions[0];
                if (!d) return jumpToStep("offering");
                // Cohort divisions (branch x batch, no semester) resolve via
                // their batch; legacy semester divisions via semester/year.
                if (!d.semester_id && d.batch_id) {
                    const b = await adminApi.getBatch(d.batch_id).catch(() => null);
                    setPath(
                        [
                            { type: "institution", data: inst },
                            b && { type: "batch", data: b },
                            { type: "division", data: d },
                        ].filter(Boolean)
                    );
                    await loadChildren("division", d.id);
                    return;
                }
                const s = (await adminApi.getSemester(d.semester_id).catch(() => null)) || stats._semesters.find((x) => x.id === d.semester_id);
                const y = s ? await pickYear(s.year_id) : null;
                const built = [
                    { type: "institution", data: inst },
                    y && { type: "year", data: y },
                    s && { type: "semester", data: s },
                    { type: "division", data: d },
                ].filter(Boolean);
                setPath(built);
                await loadChildren("division", d.id);
                return;
            }
        } finally {
            setJumping(false);
        }
    };

    const stepDone = (step) => {
        if (!stats) return false;
        if (step === "batch") return stats.batch > 0;
        if (step === "year") return stats.year > 0;
        if (step === "semester") return stats.semester > 0;
        if (step === "offering") return stats.subject > 0 && stats.division > 0;
        if (step === "class") return stats.class > 0;
        return false;
    };

    const allStepsDone = CHECKLIST.every(stepDone);
    const nextStep = CHECKLIST.find((s) => !stepDone(s.key))?.key || null;

    return (
        <div data-testid="hierarchy-tree" className="space-y-6">
            {/* Status strip + guided setup */}
            <Overview
                stats={stats}
                loading={loadingRoot}
                nextStep={nextStep}
                allDone={allStepsDone}
                jumping={jumping}
                onStep={jumpToStep}
                stepDone={stepDone}
            />

            {/* Breadcrumb — the college is the root, one click back up */}
            <nav aria-label="Hierarchy location" className="flex flex-wrap items-center gap-1 text-sm">
                {path.map((node, i) => (
                    <span key={`${node.type}-${node.data.id}`} className="flex items-center gap-1">
                        {i > 0 && <CaretRight size={12} className="text-muted-foreground" />}
                        <button
                            type="button"
                            onClick={() => goToCrumb(i)}
                            data-testid={i === 0 ? "breadcrumb-root" : `breadcrumb-${node.type}-${node.data.id}`}
                            className={`px-2 py-1 font-display font-bold transition-colors ${
                                i === path.length - 1
                                    ? "text-primary underline underline-offset-4"
                                    : "text-muted-foreground hover:text-foreground"
                            }`}
                        >
                            {displayName(node.type, node.data)}
                        </button>
                    </span>
                ))}
            </nav>

            {/* Current level */}
            {loadingRoot || !current ? (
                <div className="space-y-3 rounded-lg border border-border bg-card p-6">
                    <Skeleton className="h-8 w-64" />
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-6 w-56" />
                </div>
            ) : institutions.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border bg-card p-12 text-center">
                    <Buildings size={40} weight="duotone" className="mx-auto mb-3 text-muted-foreground/50" />
                    <h2 className="font-display text-2xl font-bold tracking-tight">No institution configured</h2>
                    <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
                        This app is set up for one college. Ask your administrator to create it.
                    </p>
                </div>
            ) : (
                <NodeLevel
                    key={cacheKey(current.type, current.data.id)}
                    node={current}
                    institutionId={institutions[0]?.id}
                    childrenCache={kids[cacheKey(current.type, current.data.id)]}
                    loading={loadingKids}
                    renaming={renaming}
                    renameValue={renameValue}
                    onRenameValue={setRenameValue}
                    onStartRename={startRename}
                    onSaveRename={saveRename}
                    onCancelRename={() => setRenaming(null)}
                    onOpen={openNode}
                    onDelete={handleDelete}
                    onAdd={openCreate}
                    showTeachers={showTeachers}
                    setShowTeachers={setShowTeachers}
                />
            )}

            {/* Shared create dialog */}
            {createType && (
                <CreateEntityDialog
                    open
                    onOpenChange={(v) => {
                        if (!v) setCreateType(null);
                    }}
                    entityType={createType}
                    parentId={createParentId}
                    selectOptions={createOptions}
                    initialValues={createInitial}
                    onSuccess={handleCreateSuccess}
                />
            )}
        </div>
    );
}

function Overview({ stats, loading, nextStep, allDone, jumping, onStep, stepDone }) {
    const counts = stats
        ? [
            { key: "batch", label: "Batches", value: stats.batch },
            { key: "year", label: "Years", value: stats.year },
            { key: "semester", label: "Semesters", value: stats.semester },
            { key: "subject", label: "Subjects", value: stats.subject },
            { key: "division", label: "Divisions", value: stats.division },
            { key: "class", label: "Classes", value: stats.class },
        ]
        : [];
    return (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
            {/* Counts */}
            <div className="rounded-lg border border-border bg-card p-5 lg:col-span-3">
                <div className="text-overline mb-4 text-muted-foreground">At a glance</div>
                {loading ? (
                    <div className="grid grid-cols-3 gap-4">
                        {[1, 2, 3, 4, 5, 6].map((i) => (
                            <Skeleton key={i} className="h-14" />
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                        {counts.map((c) => (
                            <div key={c.key} data-testid={`stat-${c.key}`}>
                                <div className="font-display text-3xl font-black tracking-tighter tabular-nums">
                                    {c.value}
                                </div>
                                <div className="text-overline text-muted-foreground">{c.label}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            {/* Guided setup */}
            <div className="rounded-lg border border-border bg-primary p-5 text-primary-foreground lg:col-span-2">
                <div className="text-overline mb-1 text-accent">
                    {allDone ? "Setup complete" : "Setup guide"}
                </div>
                <div className="font-display text-xl font-bold tracking-tight">
                    {allDone ? "Ready to teach." : "Get to your first class."}
                </div>
                <p className="mt-1 text-sm text-primary-foreground/70">
                    {allDone
                        ? "Teachers can upload, students can enroll with the class QR."
                        : "Follow the steps. Each one takes you where the work happens."}
                </p>
                <ol className="mt-4 space-y-1">
                    {CHECKLIST.map((s, i) => {
                        const done = stepDone(s.key);
                        const isNext = s.key === nextStep;
                        return (
                            <li key={s.key}>
                                <button
                                    type="button"
                                    onClick={() => onStep(s.key)}
                                    disabled={jumping || done}
                                    data-testid={`checklist-step-${s.key}`}
                                    className={`flex w-full items-center gap-3 px-2 py-2 text-left transition-colors ${
                                        done
                                            ? "opacity-70"
                                            : isNext
                                                ? "bg-accent/20 outline outline-1 outline-accent/50"
                                                : "opacity-90 hover:bg-primary-foreground/5"
                                    }`}
                                >
                                    {done ? (
                                        <CheckCircle size={18} weight="fill" className="shrink-0 text-accent" />
                                    ) : (
                                        <Circle size={18} className="shrink-0 text-primary-foreground/50" />
                                    )}
                                    <span>
                                        <span className="block text-sm font-bold">
                                            {i + 1}. {s.label}
                                        </span>
                                        <span className="block text-xs text-primary-foreground/60">{s.detail}</span>
                                    </span>
                                    {isNext && !done && (
                                        <CaretRight size={14} className="ml-auto shrink-0 text-accent" />
                                    )}
                                </button>
                            </li>
                        );
                    })}
                </ol>
            </div>
        </div>
    );
}

function NodeLevel({ node, institutionId, childrenCache, loading, renaming, renameValue, onRenameValue, onStartRename, onSaveRename, onCancelRename, onOpen, onDelete, onAdd, showTeachers, setShowTeachers }) {
    const { type, data } = node;
    const config = LEVEL_CONFIG[type];
    const groups = config.childGroups || [];

    // Leaf: class gets the operations panel, branch shows its divisions
    // per batch, subject gets a detail card
    if (type === "class") {
        return <ClassDetail data={data} showTeachers={showTeachers} setShowTeachers={setShowTeachers} />;
    }
    if (type === "branch") {
        return (
            <BranchDetail
                data={data}
                institutionId={institutionId}
                renaming={renaming}
                renameValue={renameValue}
                onRenameValue={onRenameValue}
                onStartRename={onStartRename}
                onSaveRename={onSaveRename}
                onCancelRename={onCancelRename}
                onOpen={onOpen}
                onDelete={onDelete}
                onAdd={onAdd}
            />
        );
    }
    if (groups.length === 0) {
        return (
            <div className="rounded-lg border border-border bg-card p-6">
                <EntityCard
                    type={type}
                    data={data}
                    detail
                    renaming={renaming}
                    renameValue={renameValue}
                    onRenameValue={onRenameValue}
                    onStartRename={onStartRename}
                    onSaveRename={onSaveRename}
                    onCancelRename={onCancelRename}
                    onDelete={() => onDelete(type, data)}
                />
                <p className="mt-3 text-sm text-muted-foreground">
                    {type === "branch"
                        ? "Branches group years under an institution. Nothing else to configure here."
                        : "Subjects hold the study material once a teacher uploads a lecture for a class."}
                </p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Current node header */}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card p-5">
                <div className="flex min-w-0 items-center gap-3">
                    {(() => {
                        const Icon = config.icon;
                        return <Icon size={24} weight="duotone" className="shrink-0 text-primary" />;
                    })()}
                    <div className="min-w-0">
                        <div className="text-overline text-muted-foreground">{config.label}</div>
                        <div className="font-display truncate text-2xl font-bold tracking-tight">
                            {displayName(type, data)}
                        </div>
                        {displayMeta(type, data) && (
                            <div className="text-sm text-muted-foreground">{displayMeta(type, data)}</div>
                        )}
                    </div>
                </div>
                <div className="flex gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onStartRename(type, data)}
                        data-testid={`rename-${type}-${data.id}`}
                    >
                        <PencilSimple size={14} weight="duotone" className="mr-1" />
                        Rename
                    </Button>
                    {type !== "institution" && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDelete(type, data)}
                        data-testid={`delete-${type}-${data.id}`}
                        className="text-destructive hover:text-destructive"
                    >
                        <Trash size={14} weight="duotone" className="mr-1" />
                        Delete
                    </Button>
                    )}
                </div>
            </div>
            {renaming === `${type}:${data.id}` && (
                <RenameRow
                    value={renameValue}
                    onChange={onRenameValue}
                    onSave={() => onSaveRename(type, data)}
                    onCancel={onCancelRename}
                    testId={`rename-input-${type}-${data.id}`}
                />
            )}

            {/* Cohort progression timeline for batches */}
            {type === "batch" && <BatchProgression batchId={data.id} />}

            {/* Child groups */}
            {groups.map((group) => {
                const items = childrenCache?.[group.key] || [];
                const GroupIcon = group.icon;
                return (
                    <section key={group.key} aria-label={group.label}>
                        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
                            <div className="flex items-center gap-2">
                                <GroupIcon size={18} weight="duotone" className="text-primary" />
                                <h2 className="font-display text-xl font-bold tracking-tight">{group.label}</h2>
                                <Badge variant="secondary" className="tabular-nums">{items.length}</Badge>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => onAdd(group.childType, data.id)}
                                data-testid={`add-${group.childType}-btn`}
                            >
                                <Plus size={14} weight="duotone" className="mr-1" />
                                {`New ${LEVEL_CONFIG[group.childType].label}`}
                            </Button>
                        </div>
                        <p className="mb-3 text-sm text-muted-foreground">{group.hint}</p>
                        {loading && !childrenCache ? (
                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                {[1, 2, 3].map((i) => (
                                    <Skeleton key={i} className="h-28" />
                                ))}
                            </div>
                        ) : items.length === 0 ? (
                            <div className="rounded-lg border border-dashed border-border bg-card p-8 text-center">
                                <p className="text-sm text-muted-foreground">
                                    No {group.label.toLowerCase()} yet.
                                </p>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => onAdd(group.childType, data.id)}
                                    className="mt-3"
                                    data-testid={`add-${group.childType}-empty-btn`}
                                >
                                    <Plus size={14} weight="duotone" className="mr-1" />
                                    {`Add the first ${LEVEL_CONFIG[group.childType].label.toLowerCase()}`}
                                </Button>
                            </div>
                        ) : (
                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                {items.map((child, i) => (
                                    <motion.div
                                        key={child.id}
                                        initial={{ opacity: 0, y: 8 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: Math.min(i * 0.04, 0.3) }}
                                    >
                                        <EntityCard
                                            type={group.childType}
                                            data={child}
                                            renaming={renaming}
                                            renameValue={renameValue}
                                            onRenameValue={onRenameValue}
                                            onStartRename={onStartRename}
                                            onSaveRename={onSaveRename}
                                            onCancelRename={onCancelRename}
                                            onOpen={() => onOpen(group.childType, child)}
                                            onDelete={() => onDelete(group.childType, child)}
                                        />
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </section>
                );
            })}
        </div>
    );
}

function EntityCard({ type, data, detail, renaming, renameValue, onRenameValue, onStartRename, onSaveRename, onCancelRename, onOpen, onDelete }) {
    const config = LEVEL_CONFIG[type];
    const Icon = config.icon;
    const isRenaming = renaming === `${type}:${data.id}`;
    // Every card with an open handler drills somewhere: levels with children
    // open the child level, leaves open their detail view (class ops,
    // department divisions, subject info).
    const canDrill = !!onOpen;

    return (
        <div
            data-testid={`node-${type}-${data.id}`}
            className={`flex h-full flex-col border border-border bg-card p-4 transition-colors ${
                canDrill ? "cursor-pointer hover:border-primary/50" : ""
            }`}
            onClick={canDrill && !isRenaming ? onOpen : undefined}
            onKeyDown={canDrill && !isRenaming ? (e) => { if (e.key === "Enter") onOpen(); } : undefined}
            tabIndex={canDrill && !isRenaming ? 0 : undefined}
            role={canDrill ? "button" : undefined}
            aria-label={canDrill ? `Open ${displayName(type, data)}` : undefined}
        >
            <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center bg-primary text-primary-foreground">
                    <Icon size={20} weight="duotone" />
                </div>
                <div className="min-w-0 flex-1">
                    {isRenaming ? (
                        <RenameRow
                            value={renameValue}
                            onChange={onRenameValue}
                            onSave={() => onSaveRename(type, data)}
                            onCancel={onCancelRename}
                            testId={`edit-input-${type}-${data.id}`}
                            autoFocus
                        />
                    ) : (
                        <>
                            <div className="font-display truncate font-bold leading-tight">
                                {displayName(type, data)}
                            </div>
                            {displayMeta(type, data) && (
                                <div className="truncate text-xs text-muted-foreground">{displayMeta(type, data)}</div>
                            )}
                        </>
                    )}
                </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border pt-3" onClick={(e) => e.stopPropagation()}>
                {canDrill && (
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onOpen}
                        data-testid={`open-${type}-${data.id}`}
                        className="mr-auto"
                    >
                        Open
                        <CaretRight size={14} weight="bold" className="ml-1" />
                    </Button>
                )}
                {!isRenaming && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onStartRename(type, data)}
                        data-testid={`edit-${type}-${data.id}`}
                        aria-label={`Rename ${displayName(type, data)}`}
                    >
                        <PencilSimple size={14} weight="duotone" />
                    </Button>
                )}
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onDelete}
                    data-testid={`delete-${type}-${data.id}`}
                    aria-label={`Delete ${displayName(type, data)}`}
                    className="text-destructive hover:text-destructive"
                >
                    <Trash size={14} weight="duotone" />
                </Button>
            </div>
            {detail && (
                <div className="mt-2 text-xs text-muted-foreground">
                    {type === "branch" && "Leaf level — nothing else to configure."}
                    {type === "subject" && "Lectures uploaded to this subject's classes generate study material."}
                </div>
            )}
        </div>
    );
}

function RenameRow({ value, onChange, onSave, onCancel, testId, autoFocus }) {
    return (
        <div className="flex w-full items-center gap-2">
            <Input
                autoFocus={autoFocus}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === "Enter") onSave();
                    if (e.key === "Escape") onCancel();
                }}
                data-testid={testId}
                className="h-8 text-sm"
            />
            <Button size="sm" onClick={onSave} data-testid={`${testId}-save`}>
                Save
            </Button>
            <Button size="sm" variant="ghost" onClick={onCancel} aria-label="Cancel rename">
                <CaretLeft size={14} weight="bold" />
            </Button>
        </div>
    );
}

function currentRowByDate(rows) {
    const now = new Date().toISOString().slice(0, 10);
    return rows.find((r) => r.starts_on <= now && r.ends_on >= now) || null;
}

function BatchProgression({ batchId }) {
    const [rows, setRows] = useState([]);
    const [semesters, setSemesters] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            setLoading(true);
            try {
                const [r, s] = await Promise.all([
                    adminApi.listBatchSemesters(batchId).catch(() => []),
                    adminApi.listSemesters().catch(() => []),
                ]);
                if (!cancelled) {
                    setRows(r || []);
                    setSemesters(s || []);
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        })();
        return () => { cancelled = true; };
    }, [batchId]);

    if (loading) return <Skeleton className="h-20" />;
    if (rows.length === 0) return null;

    const byId = Object.fromEntries(semesters.map((s) => [s.id, s]));
    const ordered = [...rows].sort((a, b) => (byId[a.semester_id]?.number ?? 0) - (byId[b.semester_id]?.number ?? 0));
    const now = new Date().toISOString().slice(0, 10);

    return (
        <section aria-label="Cohort progression" className="rounded-lg border border-border bg-card p-4">
            <div className="text-overline mb-3 text-muted-foreground">Cohort progression — derived from term dates</div>
            <ol className="flex flex-wrap items-stretch gap-2">
                {ordered.map((r) => {
                    const sem = byId[r.semester_id];
                    const isCurrent = r.starts_on <= now && r.ends_on >= now;
                    const isPast = r.ends_on < now;
                    return (
                        <li
                            key={r.id}
                            data-testid={`progression-chip-${sem?.number ?? r.id.slice(0, 8)}`}
                            title={`${sem?.label || "Semester"} · ${r.academic_year} (${r.starts_on} to ${r.ends_on})`}
                            className={`min-w-20 flex-1 border px-3 py-2 text-center transition-colors ${
                                isCurrent
                                    ? "border-primary bg-primary text-primary-foreground"
                                    : isPast
                                        ? "border-border bg-muted/50 text-muted-foreground"
                                        : "border-border bg-card text-foreground"
                            }`}
                        >
                            <div className="font-display text-sm font-bold">
                                {isCurrent ? "Now · " : ""}Sem {sem?.number ?? "?"}
                            </div>
                            <div className={`text-xs tabular-nums ${isCurrent ? "text-primary-foreground/80" : "text-muted-foreground"}`}>
                                {r.academic_year}
                            </div>
                        </li>
                    );
                })}
            </ol>
        </section>
    );
}

function BranchDetail({ data, institutionId, renaming, renameValue, onRenameValue, onStartRename, onSaveRename, onCancelRename, onOpen, onDelete, onAdd }) {
    const [batches, setBatches] = useState([]);
    const [divisions, setDivisions] = useState([]);
    const [progression, setProgression] = useState({});
    const [semesters, setSemesters] = useState([]);
    const [loading, setLoading] = useState(true);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const [b, d, s] = await Promise.all([
                (institutionId ? adminApi.listInstitutionBatches(institutionId) : Promise.resolve([])).catch(() => []),
                adminApi.listBranchDivisions(data.id).catch(() => []),
                adminApi.listSemesters().catch(() => []),
            ]);
            const sorted = (b || []).slice().sort((x, y) => x.graduating_year - y.graduating_year);
            setBatches(sorted);
            setDivisions(d || []);
            setSemesters(s || []);
            const rows = await Promise.all(
                sorted.map((batch) => adminApi.listBatchSemesters(batch.id).catch(() => []))
            );
            const prog = {};
            sorted.forEach((batch, i) => { prog[batch.id] = currentRowByDate(rows[i] || []); });
            setProgression(prog);
        } finally {
            setLoading(false);
        }
    }, [data.id, institutionId]);

    useEffect(() => {
        load();
    }, [load]);

    const byBatch = (batchId) => divisions.filter((d) => d.batch_id === batchId);

    return (
        <div className="space-y-6">
            <div className="rounded-lg border border-border bg-card p-6">
                <EntityCard
                    type="branch"
                    data={data}
                    detail
                    renaming={renaming}
                    renameValue={renameValue}
                    onRenameValue={onRenameValue}
                    onStartRename={onStartRename}
                    onSaveRename={onSaveRename}
                    onCancelRename={onCancelRename}
                    onDelete={() => onDelete("branch", data)}
                />
                <p className="mt-3 text-sm text-muted-foreground">
                    Divisions below belong to this department, grouped by graduating batch —
                    so CSE can have one division for 2028 and A/B/C for 2029.
                </p>
            </div>

            {loading ? (
                <div className="grid gap-3 sm:grid-cols-2">
                    {[1, 2].map((i) => (
                        <Skeleton key={i} className="h-28" />
                    ))}
                </div>
            ) : batches.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border bg-card p-8 text-center">
                    <p className="text-sm text-muted-foreground">
                        No batches yet. Create a batch first, then add this department's divisions to it.
                    </p>
                </div>
            ) : (
                batches.map((batch) => {
                    const items = byBatch(batch.id);
                    const current = progression[batch.id];
                    const currentSem = current && semesters.find((s) => s.id === current.semester_id);
                    return (
                        <section key={batch.id} aria-label={`${displayName("batch", batch)} divisions`}>
                            <div className="mb-1 flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
                                <div className="flex items-center gap-2">
                                    <GraduationCap size={18} weight="duotone" className="text-primary" />
                                    <h2 className="font-display text-xl font-bold tracking-tight">
                                        {displayName("batch", batch)}
                                    </h2>
                                    <Badge variant="secondary" className="tabular-nums">{items.length}</Badge>
                                    {current && (
                                        <Badge className="bg-accent text-accent-foreground" data-testid={`batch-current-${batch.id}`}>
                                            Currently in {currentSem?.label || `Semester ${currentSem?.number ?? ""}`.trim()} · {current.academic_year}
                                        </Badge>
                                    )}
                                </div>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => onAdd("division", null, {
                                        initial: { branch_id: data.id, batch_id: batch.id },
                                    })}
                                    data-testid={`add-division-${batch.id}-btn`}
                                >
                                    <Plus size={14} weight="duotone" className="mr-1" />
                                    New Division
                                </Button>
                            </div>
                            {items.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-border bg-card p-6 text-center">
                                    <p className="text-sm text-muted-foreground">
                                        No {displayName("branch", data)} divisions for {displayName("batch", batch)} yet.
                                    </p>
                                </div>
                            ) : (
                                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                                    {items.map((div, i) => (
                                        <motion.div
                                            key={div.id}
                                            initial={{ opacity: 0, y: 8 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: Math.min(i * 0.04, 0.3) }}
                                        >
                                            <EntityCard
                                                type="division"
                                                data={div}
                                                renaming={renaming}
                                                renameValue={renameValue}
                                                onRenameValue={onRenameValue}
                                                onStartRename={onStartRename}
                                                onSaveRename={onSaveRename}
                                                onCancelRename={onCancelRename}
                                                onOpen={() => onOpen("division", div)}
                                                onDelete={() => Promise.resolve(onDelete("division", div)).then(load)}
                                            />
                                        </motion.div>
                                    ))}
                                </div>
                            )}
                        </section>
                    );
                })
            )}
        </div>
    );
}

function ClassDetail({ data, showTeachers, setShowTeachers }) {
    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card p-5">
                <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center bg-accent text-accent-foreground">
                        <ChalkboardTeacher size={24} weight="duotone" />
                    </div>
                    <div>
                        <div className="text-overline text-muted-foreground">Class</div>
                        <div className="font-display text-2xl font-bold tracking-tight">
                            {displayName("class", data)}
                        </div>
                    </div>
                </div>
                <Button
                    onClick={() => setShowTeachers(true)}
                    data-testid={`manage-teachers-${data.id}`}
                >
                    <UsersThree size={16} weight="duotone" className="mr-2" />
                    Manage teachers
                </Button>
            </div>

            <div className="rounded-lg border border-border bg-card p-5">
                <div className="text-overline mb-1 text-muted-foreground">Step 1 — Staff the class</div>
                <p className="text-sm text-muted-foreground">
                    Assign teachers so they can upload lectures here. Students join in step 2.
                </p>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowTeachers(true)}
                    className="mt-3"
                    data-testid={`manage-teachers-cta-${data.id}`}
                >
                    <UsersThree size={14} weight="duotone" className="mr-1" />
                    Assign teachers
                </Button>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
                <div>
                    <div className="text-overline mb-2 text-muted-foreground">Step 2 — Enroll students</div>
                    <QRCodeCard classId={data.id} className={data.name || "Class"} />
                    <p className="mt-2 flex items-start gap-2 text-xs text-muted-foreground">
                        <QrCode size={14} className="mt-0.5 shrink-0" />
                        Students scan this QR to enroll themselves. Regenerating invalidates the old code.
                    </p>
                </div>
                <div>
                    <div className="text-overline mb-2 text-muted-foreground">Step 3 — Check enrollment</div>
                    <EnrollmentTable classId={data.id} className={data.name || "Class"} />
                </div>
            </div>

            <TeacherAssignmentPanel
                open={showTeachers}
                onOpenChange={setShowTeachers}
                classId={data.id}
                className={data.name || "Class"}
            />
        </div>
    );
}
