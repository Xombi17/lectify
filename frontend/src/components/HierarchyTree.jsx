import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    CaretRight,
    Buildings,
    GitBranch,
    CalendarBlank,
    BookBookmark,
    UsersThree,
    ChalkboardTeacher,
    Plus,
    PencilSimple,
    Trash,
} from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { adminApi } from "@/lib/api";
import { toast } from "sonner";
import CreateEntityDialog from "@/components/CreateEntityDialog";
import TeacherAssignmentPanel from "@/components/TeacherAssignmentPanel";
import QRCodeCard from "@/components/QRCodeCard";
import EnrollmentTable from "@/components/EnrollmentTable";

// Tree config: each node type has its load function and children types
const TREE_CONFIG = {
    institution: {
        icon: Buildings,
        label: "Institution",
        createLabel: "New Institution",
        listAll: () => adminApi.listInstitutions(),
        childGroups: [
            {
                key: "years",
                label: "Years",
                icon: CalendarBlank,
                listFn: (id) => adminApi.listInstitutionYears(id),
                childType: "year",
            },
            {
                key: "branches",
                label: "Branches",
                icon: GitBranch,
                listFn: (id) => adminApi.listInstitutionBranches(id),
                childType: "branch",
            },
        ],
    },
    year: {
        icon: CalendarBlank,
        label: "Year",
        createLabel: "New Year",
        childGroups: [
            {
                key: "semesters",
                label: "Semesters",
                icon: CalendarBlank,
                listFn: (id) => adminApi.listYearSemesters(id),
                childType: "semester",
            },
        ],
    },
    branch: {
        icon: GitBranch,
        label: "Branch",
        createLabel: "New Branch",
        // Leaf node — no children
    },
    semester: {
        icon: CalendarBlank,
        label: "Semester",
        createLabel: "New Semester",
        childGroups: [
            {
                key: "subjects",
                label: "Subjects",
                icon: BookBookmark,
                listFn: (id) => adminApi.listSemesterSubjects(id),
                childType: "subject",
            },
            {
                key: "divisions",
                label: "Divisions",
                icon: UsersThree,
                listFn: (id) => adminApi.listSemesterDivisions(id),
                childType: "division",
            },
        ],
    },
    subject: {
        icon: BookBookmark,
        label: "Subject",
        createLabel: "New Subject",
        // Leaf node
    },
    division: {
        icon: UsersThree,
        label: "Division",
        createLabel: "New Division",
        childGroups: [
            {
                key: "classes",
                label: "Classes",
                icon: ChalkboardTeacher,
                listFn: (id) => adminApi.listDivisionClasses(id),
                childType: "class",
            },
        ],
    },
    class: {
        icon: ChalkboardTeacher,
        label: "Class",
        createLabel: "New Class",
        // Leaf node — shows action panels instead of children
    },
};

function getDisplayName(configKey, data) {
    if (data.name) return data.name;
    if (data.code) return data.code;
    if (data.label) return data.label;
    if (configKey === "class") return `Class ${data.id.slice(0, 8)}`;
    return data.id.slice(0, 8);
}

function HierarchyNode({ configKey, data, depth = 0, onRefresh }) {
    const [expanded, setExpanded] = useState(false);
    const [loading, setLoading] = useState(false);
    const [children, setChildren] = useState({});
    const [editing, setEditing] = useState(false);
    const [editValue, setEditValue] = useState("");
    const [showCreate, setShowCreate] = useState(false);
    const [createType, setCreateType] = useState(null);
    const [showAssignments, setShowAssignments] = useState(false);

    const config = TREE_CONFIG[configKey];
    const Icon = config.icon;
    const hasChildren = config.childGroups && config.childGroups.length > 0;

    const loadChildren = useCallback(async () => {
        if (!config.childGroups) return;
        setLoading(true);
        try {
            const results = {};
            for (const group of config.childGroups) {
                const items = await group.listFn(data.id);
                results[group.key] = items || [];
            }
            setChildren(results);
        } catch (err) {
            toast.error(`Failed to load ${config.label} children`);
        } finally {
            setLoading(false);
        }
    }, [config, data.id]);

    const handleToggle = () => {
        if (!hasChildren) return;
        const newExpanded = !expanded;
        setExpanded(newExpanded);
        if (newExpanded && Object.keys(children).length === 0) {
            loadChildren();
        }
    };

    const handleDelete = async () => {
        if (!window.confirm(`Delete "${getDisplayName(configKey, data)}"?`)) return;
        try {
            const deleteMap = {
                institution: adminApi.deleteInstitution,
                year: adminApi.deleteYear,
                branch: adminApi.deleteBranch,
                semester: adminApi.deleteSemester,
                subject: adminApi.deleteSubject,
                division: adminApi.deleteDivision,
                class: adminApi.deleteClass,
            };
            await deleteMap[configKey](data.id);
            toast.success(`${config.label} deleted`);
            if (onRefresh) onRefresh();
        } catch (err) {
            toast.error(`Failed to delete ${config.label}`);
        }
    };

    const handleEditStart = () => {
        setEditValue(getDisplayName(configKey, data));
        setEditing(true);
    };

    const handleEditSave = async () => {
        if (!editValue.trim()) return;
        try {
            const updateMap = {
                institution: () => adminApi.updateInstitution(data.id, { name: editValue, code: data.code, address: data.address }),
                year: () => adminApi.updateYear(data.id, { name: editValue, number: data.number, institution_id: data.institution_id }),
                branch: () => adminApi.updateBranch(data.id, { name: editValue, code: data.code, institution_id: data.institution_id }),
                semester: () => adminApi.updateSemester(data.id, { label: editValue, number: data.number, year_id: data.year_id }),
                subject: () => adminApi.updateSubject(data.id, { name: editValue, code: data.code, semester_id: data.semester_id, credits: data.credits }),
                division: () => adminApi.updateDivision(data.id, { name: editValue, semester_id: data.semester_id, capacity: data.capacity }),
                class: () => adminApi.updateClass(data.id, { name: editValue, division_id: data.division_id, subject_id: data.subject_id }),
            };
            await updateMap[configKey]();
            toast.success(`${config.label} updated`);
            setEditing(false);
            if (onRefresh) onRefresh();
        } catch (err) {
            toast.error(`Failed to update ${config.label}`);
        }
    };

    const handleEditCancel = () => {
        setEditing(false);
        setEditValue("");
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter") handleEditSave();
        if (e.key === "Escape") handleEditCancel();
    };

    const handleCreate = (childType) => {
        setCreateType(childType);
        setShowCreate(true);
    };

    const handleCreateSuccess = () => {
        loadChildren();
    };

    const indentPx = depth * 24;

    return (
        <div className="relative">
            {/* Node row */}
            <div
                className="group flex items-center gap-2 py-1.5 px-2 rounded-md hover:bg-muted/50 transition-colors"
                style={{ paddingLeft: `${indentPx + 8}px` }}
                data-testid={`node-${configKey}-${data.id}`}
            >
                {/* Expand/collapse */}
                {hasChildren ? (
                    <button
                        onClick={handleToggle}
                        className="p-0.5 rounded hover:bg-muted transition-colors"
                        data-testid={`expand-${configKey}-${data.id}`}
                        aria-label={expanded ? "Collapse" : "Expand"}
                    >
                        <motion.div
                            animate={{ rotate: expanded ? 90 : 0 }}
                            transition={{ duration: 0.15 }}
                        >
                            <CaretRight size={14} className="text-muted-foreground" />
                        </motion.div>
                    </button>
                ) : (
                    <div className="w-5" />
                )}

                {/* Icon + Name */}
                <Icon size={16} className="text-primary shrink-0" />

                {editing ? (
                    <input
                        autoFocus
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        onBlur={handleEditSave}
                        className="flex-1 text-sm bg-background border border-border rounded px-2 py-0.5 outline-none focus:ring-2 focus:ring-primary/30"
                        data-testid={`edit-input-${configKey}-${data.id}`}
                    />
                ) : (
                    <span className="flex-1 text-sm font-medium truncate">
                        {getDisplayName(configKey, data)}
                    </span>
                )}

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {/* Create child buttons */}
                    {config.childGroups?.map((group) => (
                        <Button
                            key={group.key}
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => handleCreate(group.childType)}
                            data-testid={`add-${group.childType}-${data.id}`}
                            title={`Add ${group.label}`}
                        >
                            <Plus size={13} />
                        </Button>
                    ))}
                    {/* Class-specific: Teachers button */}
                    {configKey === "class" && (
                        <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 text-xs"
                            onClick={() => setShowAssignments(true)}
                            data-testid={`manage-teachers-${data.id}`}
                        >
                            <UsersThree size={13} className="mr-1" />
                            Teachers
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={handleEditStart}
                        data-testid={`edit-${configKey}-${data.id}`}
                    >
                        <PencilSimple size={13} />
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-destructive hover:text-destructive"
                        onClick={handleDelete}
                        data-testid={`delete-${configKey}-${data.id}`}
                    >
                        <Trash size={13} />
                    </Button>
                </div>
            </div>

            {/* Teacher Assignment Dialog (for Class nodes) */}
            {configKey === "class" && (
                <TeacherAssignmentPanel
                    open={showAssignments}
                    onOpenChange={setShowAssignments}
                    classId={data.id}
                    className={data.name || "Class"}
                />
            )}

            {/* Create Entity Dialog */}
            {createType && (
                <CreateEntityDialog
                    open={showCreate}
                    onOpenChange={setShowCreate}
                    entityType={createType}
                    parentId={data.id}
                    onSuccess={handleCreateSuccess}
                />
            )}

            {/* Class detail panels (shown when Class node is expanded) */}
            {expanded && configKey === "class" && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                >
                    <div
                        className="mt-2 space-y-4 border-l border-border/40 pl-4 py-2"
                        style={{ marginLeft: `${indentPx + 15}px` }}
                    >
                        <QRCodeCard classId={data.id} className={data.name || "Class"} />
                        <EnrollmentTable classId={data.id} className={data.name || "Class"} />
                    </div>
                </motion.div>
            )}

            {/* Children */}
            <AnimatePresence>
                {expanded && hasChildren && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        {/* Vertical tree line */}
                        <div
                            className="border-l border-border/40 ml-3"
                            style={{ marginLeft: `${indentPx + 15}px` }}
                        >
                            {loading ? (
                                <div className="py-2 space-y-2" style={{ paddingLeft: "16px" }}>
                                    <Skeleton className="h-5 w-48" />
                                    <Skeleton className="h-5 w-36" />
                                </div>
                            ) : (
                                config.childGroups.map((group) => {
                                    const items = children[group.key] || [];
                                    const GroupIcon = group.icon;
                                    return (
                                        <div key={group.key} className="py-1">
                                            {/* Group header */}
                                            <div
                                                className="flex items-center gap-1.5 py-1 px-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider"
                                                style={{ paddingLeft: "16px" }}
                                            >
                                                <GroupIcon size={12} />
                                                {group.label}
                                                <span className="text-muted-foreground/60">({items.length})</span>
                                            </div>

                                            {/* Child nodes */}
                                            {items.length === 0 ? (
                                                <div
                                                    className="text-xs text-muted-foreground italic py-1 px-2"
                                                    style={{ paddingLeft: "32px" }}
                                                >
                                                    No {group.label.toLowerCase()} yet
                                                </div>
                                            ) : (
                                                items.map((child) => (
                                                    <HierarchyNode
                                                        key={child.id}
                                                        configKey={group.childType}
                                                        data={child}
                                                        depth={depth + 1}
                                                        onRefresh={loadChildren}
                                                    />
                                                ))
                                            )}
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default function HierarchyTree() {
    const [institutions, setInstitutions] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadInstitutions = useCallback(async () => {
        setLoading(true);
        try {
            const data = await adminApi.listInstitutions();
            setInstitutions(data || []);
        } catch (err) {
            toast.error("Failed to load institutions");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadInstitutions();
    }, [loadInstitutions]);

    return (
        <div data-testid="hierarchy-tree" className="rounded-lg border bg-card p-4">
            {loading ? (
                <div className="space-y-3">
                    <Skeleton className="h-8 w-64" />
                    <Skeleton className="h-6 w-48" />
                    <Skeleton className="h-6 w-56" />
                </div>
            ) : institutions.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                    <Buildings size={40} className="mx-auto mb-3 opacity-30" />
                    <p className="text-sm">No institutions yet. Create one to get started.</p>
                </div>
            ) : (
                institutions.map((inst) => (
                    <HierarchyNode
                        key={inst.id}
                        configKey="institution"
                        data={inst}
                        depth={0}
                        onRefresh={loadInstitutions}
                    />
                ))
            )}
        </div>
    );
}