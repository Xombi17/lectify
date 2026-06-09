import { useState, useEffect, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { assignmentApi } from "@/lib/api";
import { Trash, Plus } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function TeacherAssignmentPanel({ open, onOpenChange, classId, className }) {
    const [teachers, setTeachers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [teacherIdInput, setTeacherIdInput] = useState("");
    const [adding, setAdding] = useState(false);

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
        if (open) load();
    }, [open, load]);

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
                    <Input
                        placeholder="Teacher ID"
                        value={teacherIdInput}
                        onChange={(e) => setTeacherIdInput(e.target.value)}
                        data-testid="teacher-id-input"
                    />
                    <Button onClick={handleAdd} disabled={adding} data-testid="assign-teacher-btn">
                        <Plus size={16} weight="duotone" className="mr-1" />
                        Assign
                    </Button>
                </div>

                {/* Assigned teachers table */}
                {loading ? (
                    <div className="h-20 animate-pulse bg-muted/40 rounded" />
                ) : teachers.length === 0 ? (
                    <p className="py-4 text-center text-sm text-muted-foreground">No teachers assigned</p>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Teacher ID</TableHead>
                                <TableHead>Assigned</TableHead>
                                <TableHead className="w-12" />
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {teachers.map((t) => (
                                <TableRow key={t.id} data-testid={`assignment-row-${t.id}`}>
                                    <TableCell className="font-mono text-sm">{t.teacher_id}</TableCell>
                                    <TableCell className="text-sm text-muted-foreground">
                                        {new Date(t.assigned_at).toLocaleDateString()}
                                    </TableCell>
                                    <TableCell>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => handleRemove(t.id)}
                                            data-testid={`remove-assignment-${t.id}`}
                                        >
                                            <Trash size={14} weight="duotone" className="text-destructive" />
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </DialogContent>
        </Dialog>
    );
}