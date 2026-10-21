import { Check, HourglassMedium, Warning } from "@/components/icons";
import { cn } from "@/lib/utils";
import { STATUS_LABEL, statusPillKind } from "@/lib/lectureStatus";

const CLS = { ready: "stamp-ready", processing: "stamp-proc", failed: "stamp-fail" };
const ICON = { ready: Check, processing: HourglassMedium, failed: Warning };
const FALLBACK = { ready: "Ready", processing: "Writing up", failed: "Retry processing" };

// extra props (e.g. a different data-testid) pass through to the chip
export default function StatusStamp({ status, className, ...rest }) {
    const kind = statusPillKind(status);
    const Icon = ICON[kind];
    return (
        <span data-testid="status-badge" data-kind={kind} className={cn("stamp", CLS[kind], className)} {...rest}>
            <Icon aria-hidden="true" weight="bold" size={16} />
            {STATUS_LABEL[status] ?? FALLBACK[kind]}
        </span>
    );
}
