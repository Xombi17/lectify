import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { enrollmentApi } from "@/lib/api";
import { Users } from "@/components/icons";

export default function EnrollmentTable({ classId, className }) {
    const [students, setStudents] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!classId) return;
        setLoading(true);
        enrollmentApi
            .listForClass(classId)
            .then(setStudents)
            .catch(() => setStudents([]))
            .finally(() => setLoading(false));
    }, [classId]);

    return (
        <Card data-testid={`enrollment-card-${classId}`}>
            <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                    <Users size={16} weight="regular" className="text-primary" />
                    Enrolled Students
                    <span className="ml-auto text-overline text-muted-foreground">
                        {students.length} total
                    </span>
                </CardTitle>
            </CardHeader>
            <CardContent>
                {loading ? (
                    <div className="space-y-2">
                        {[1, 2, 3].map((i) => (
                            <div key={i} className="h-10 animate-pulse rounded-[var(--r)] bg-muted/40" />
                        ))}
                    </div>
                ) : students.length === 0 ? (
                    <div className="empty">
                        <h3>A blank page</h3>
                        <p>No students have joined this class yet. Share the class QR code to enrol them.</p>
                    </div>
                ) : (
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Student ID</TableHead>
                                <TableHead>Enrolled</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {students.map((s) => (
                                <TableRow key={s.id} data-testid={`enrollment-row-${s.id}`}>
                                    <TableCell className="font-bold">{s.student_id}</TableCell>
                                    <TableCell className="font-mono text-sm text-muted-foreground">
                                        {new Date(s.enrolled_at).toLocaleDateString()}
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </CardContent>
        </Card>
    );
}