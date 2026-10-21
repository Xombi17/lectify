import {
    AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
    AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function ConfirmDialog({
    open, onOpenChange, title, description, confirmLabel,
    cancelLabel = "Keep it", onConfirm, testId = "confirm-dialog",
}) {
    return (
        <AlertDialog open={open} onOpenChange={onOpenChange}>
            <AlertDialogContent data-testid={testId}>
                <AlertDialogHeader>
                    <AlertDialogTitle>{title}</AlertDialogTitle>
                    {description && <AlertDialogDescription>{description}</AlertDialogDescription>}
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel data-testid={`${testId}-cancel`}>{cancelLabel}</AlertDialogCancel>
                    <AlertDialogAction data-testid={`${testId}-confirm`} onClick={async () => { await onConfirm?.(); }}>
                        {confirmLabel}
                    </AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    );
}
