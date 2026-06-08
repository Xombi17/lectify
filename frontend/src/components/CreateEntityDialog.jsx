import { useState, useEffect } from "react";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { adminApi } from "@/lib/api";
import { toast } from "sonner";

// Field configs per entity type — derived from Pydantic Create models
const ENTITY_FIELDS = {
    institution: [
        { key: "name", label: "Name", required: true },
        { key: "code", label: "Code", required: true },
        { key: "address", label: "Address", required: false },
    ],
    year: [
        { key: "number", label: "Year Number", required: true, type: "number", placeholder: "e.g. 1, 2, 3" },
        { key: "name", label: "Year Name", required: true, placeholder: "e.g. First Year" },
        { key: "institution_id", label: "Institution ID", hidden: true },
    ],
    branch: [
        { key: "name", label: "Name", required: true },
        { key: "code", label: "Code", required: true },
        { key: "institution_id", label: "Institution ID", hidden: true },
    ],
    semester: [
        { key: "number", label: "Semester Number", required: true, type: "number", placeholder: "e.g. 1, 2" },
        { key: "label", label: "Label", required: true, placeholder: "e.g. Fall 2025" },
        { key: "year_id", label: "Year ID", hidden: true },
    ],
    subject: [
        { key: "name", label: "Name", required: true },
        { key: "code", label: "Code", required: true },
        { key: "credits", label: "Credits", required: false, type: "number" },
        { key: "semester_id", label: "Semester ID", hidden: true },
    ],
    division: [
        { key: "name", label: "Name", required: true },
        { key: "capacity", label: "Capacity", required: false, type: "number", placeholder: "Max students" },
        { key: "semester_id", label: "Semester ID", hidden: true },
    ],
    class: [
        { key: "name", label: "Display Name", required: false, placeholder: "Optional display name" },
        { key: "subject_id", label: "Subject ID", required: true },
        { key: "division_id", label: "Division ID", hidden: true },
    ],
};

// API create methods per entity type
const CREATE_FNS = {
    institution: adminApi.createInstitution,
    year: adminApi.createYear,
    branch: adminApi.createBranch,
    semester: adminApi.createSemester,
    subject: adminApi.createSubject,
    division: adminApi.createDivision,
    class: adminApi.createClass,
};

// Fields that need string→int conversion
const NUMBER_FIELDS = ["number", "credits", "capacity"];

export default function CreateEntityDialog({ open, onOpenChange, entityType, parentId, onSuccess }) {
    const [values, setValues] = useState({});
    const [loading, setLoading] = useState(false);
    const fields = ENTITY_FIELDS[entityType] || [];

    // Reset form when dialog opens
    useEffect(() => {
        if (open) setValues({});
    }, [open]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            const payload = { ...values };

            // Inject parent ID for child entities
            const hiddenField = fields.find((f) => f.hidden);
            if (hiddenField) payload[hiddenField.key] = parentId;

            // Convert number fields from string to int
            for (const key of NUMBER_FIELDS) {
                if (payload[key] !== undefined && payload[key] !== "") {
                    payload[key] = parseInt(payload[key], 10);
                } else if (payload[key] === "" && fields.find((f) => f.key === key && !f.required)) {
                    delete payload[key];
                }
            }

            await CREATE_FNS[entityType](payload);
            toast.success(`${entityType.charAt(0).toUpperCase() + entityType.slice(1)} created`);
            if (onSuccess) onSuccess();
            onOpenChange(false);
            setValues({});
        } catch (err) {
            toast.error(`Failed to create ${entityType}`);
        } finally {
            setLoading(false);
        }
    };

    const entityLabel = entityType.charAt(0).toUpperCase() + entityType.slice(1);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent data-testid={`create-dialog-${entityType}`}>
                <DialogHeader>
                    <DialogTitle>Create {entityLabel}</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4">
                    {fields
                        .filter((f) => !f.hidden)
                        .map((field) => (
                            <div key={field.key}>
                                <label className="text-overline text-muted-foreground block mb-1">
                                    {field.label}
                                    {field.required && <span className="text-destructive ml-1">*</span>}
                                </label>
                                <Input
                                    value={values[field.key] || ""}
                                    onChange={(e) =>
                                        setValues((v) => ({ ...v, [field.key]: e.target.value }))
                                    }
                                    required={field.required}
                                    type={field.type || "text"}
                                    placeholder={field.placeholder || ""}
                                    data-testid={`create-${entityType}-${field.key}`}
                                />
                            </div>
                        ))}
                    <DialogFooter>
                        <Button
                            type="button"
                            variant="ghost"
                            onClick={() => onOpenChange(false)}
                            data-testid={`create-${entityType}-cancel`}
                        >
                            Cancel
                        </Button>
                        <Button
                            type="submit"
                            disabled={loading}
                            data-testid={`create-${entityType}-submit`}
                        >
                            {loading ? "Creating..." : `Create ${entityLabel}`}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}