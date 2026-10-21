/**
 * Lecture status to stamp mapping (Phase 20 UI-SPEC).
 *
 * ready -> Ready (content enabled)
 * uploading / queued / processing / retrying / uploaded / verifying -> Writing up
 * error / dead_letter -> Retry processing (player hidden)
 */
export const STATUS_LABEL = {
    ready: "Ready",
    uploading: "Writing up",
    queued: "Writing up",
    processing: "Writing up",
    retrying: "Writing up",
    uploaded: "Writing up",
    verifying: "Writing up",
    error: "Retry processing",
    dead_letter: "Retry processing",
};

export const FAILED_MESSAGE =
    "This lecture could not be processed. Retry, or ask an admin if it keeps failing.";

export function statusPillKind(status) {
    if (status === "ready") return "ready";
    if (status === "error" || status === "dead_letter") return "failed";
    return "processing";
}

export function isTerminalStatus(status) {
    return status === "ready" || status === "error" || status === "dead_letter";
}
