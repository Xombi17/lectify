/**
 * Lecture status → pill mapping (Phase 16 UI-SPEC).
 *
 * ready → Ready (content enabled)
 * uploading / queued / processing / retrying / uploaded → Processing
 * error / dead_letter → Failed (player hidden, contact-teacher copy)
 */
export const STATUS_LABEL = {
    ready: "Ready",
    uploading: "Processing",
    queued: "Processing",
    processing: "Processing",
    retrying: "Processing",
    uploaded: "Processing",
    error: "Processing failed — contact your teacher",
    dead_letter: "Processing failed — contact your teacher",
};

export function statusPillKind(status) {
    if (status === "ready") return "ready";
    if (status === "error" || status === "dead_letter") return "failed";
    return "processing";
}

export function isTerminalStatus(status) {
    return status === "ready" || status === "error" || status === "dead_letter";
}
