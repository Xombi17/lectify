import { useState, useEffect, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import ConfirmDialog from "@/components/ConfirmDialog";
import { assignmentApi } from "@/lib/api";
import { Trash, Plus } from "@/components/icons";
import { toast } from "sonner";

export default function TeacherAssignmentPanel({ open, onOpenChange, classId, className }) {
    const [teachers, setTeachers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [teacherIdInput, setTeacherIdInput] = useState("");
    const [adding, setAdding] = useState(false);
    const [teacherOptions, setTeacherOptions] = useState([]);
    const [pendingRemove, setPendingRemove] = useState(null);

    const load = useCallback(async () => {
        if (!classId) return;
        setLoading(true);
        try {
            setTeachers(await assignmentApi.listForClass(classId));
        } finally {
            setLoading(false);
        }
    }, [classId]);

    useEffect(() => {
        if (!open) return;
        load();
        assignmentApi.listTeachers().then(setTeacherOptions).catch(() => toast.error("Could not load teachers"));
    }, [open, load]);

    const teacherLabel = (id) => {
        const t = teacherOptions.find((o) => o.id === id);
        return t ? `${t.name} (${t.email})` : id;
    };

    const handleAdd = async () => {
        if (!teacherIdInput.trim()) return;
        setAdding(true);
        try {
            await assignmentApi.assign({ class_id: classId, teacher_id: teacherIdInput.trim() });
            setTeacherIdInput("");
            await load();
            toast.success("Teacher assigned");
        } catch (err) {
            toast.error(err?.response?.data?.detail || "Assignment failed");
        } finally {
            setAdding(false);
        }
    };

    const handleRemove = async (assignmentId) => {
        try {
            await assignmentApi.remove(assignmentId);
            await load();
            toast.success("Teacher unassigned");
        } catch {
            toast.error("Failed to unassign");
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg" data-testid="teacher-assignment-dialog">
                <DialogHeader>
                    <DialogTitle>Teacher Assignments — {className}</DialogTitle>
                </DialogHeader>

                {/* Add teacher input */}
                <div className="flex gap-2">
                    <select
                        value={teacherIdInput}
                        onChange={(e) => setTeacherIdInput(e.target.value)}
                        data-testid="teacher-id-input"
                        className="field w-full"
                    >
                        <option value="">Select a teacher…</option>
                        {teacherOptions
                            .filter((t) => !teachers.some((a) => a.teacher_id === t.id))
                            .map((t) => (
                                <option key={t.id} value={t.id}>
                                    {t.name} ({t.email})
                                </option>
                            ))}
                    </select>
                    <Button variant="pen" onClick={handleAdd} disabled={adding || !teacherIdInput} data-testid="assign-teacher-btn">
                        <Plus size={16} weight="regular" className="mr-1" />
                        Assign
                    </Button>
                </div>

                {/* Assigned teachers table */}
                {loading ? (
                    <div className="h-20 animate-pulse rounded-[var(--r)] bg-muted/40" />
                ) : teachers.length === 0 ? (
                    <p className="py-4 text-center text-sm text-muted-foreground">No teachers assigned</p>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Teacher</TableHead>
                                <TableHead>Assigned</TableHead>
                                <TableHead className="w-12" />
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {teachers.map((t) => (
                                <TableRow key={t.id} data-testid={`assignment-row-${t.id}`}>
                                    <TableCell className="text-sm">{teacherLabel(t.teacher_id)}</TableCell>
                                    <TableCell className="text-sm text-muted-foreground">
                                        {new Date(t.assigned_at).toLocaleDateString()}
                                    </TableCell>
                                    <TableCell>
                                        <Button
                                            variant="quiet"
                                            size="sm"
                                            aria-label={`Remove ${teacherLabel(t.teacher_id)}`}
                                            onClick={() => setPendingRemove(t)}
                                            data-testid={`remove-assignment-${t.id}`}
                                        >
                                            <Trash size={14} weight="regular" className="text-destructive" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
                <ConfirmDialog
                    open={!!pendingRemove}
                    onOpenChange={(o) => !o && setPendingRemove(null)}
                    testId="confirm-remove-teacher"
                    title={`Remove ${pendingRemove ? teacherLabel(pendingRemove.teacher_id) : "this teacher"} from ${className || "this class"}?`}
                    description="They lose upload access to it."
                    confirmLabel="Remove teacher"
                    cancelLabel="Keep teacher"
                    onConfirm={() => handleRemove(pendingRemove.id)}
                />
            </DialogContent>
        </Dialog>
    );
}