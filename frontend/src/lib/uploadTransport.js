/** Phase 16 upload transport helpers (testable pure logic). */
export const FALLBACK_NOTICE = "Direct upload unavailable — using standard upload.";
export const MISSING_OBJECT_MSG = "Upload did not reach storage. Try again.";
export const OVERSIZE_MSG = "File too large (max 200 MB).";
export const VERIFYING_LABEL = "Verifying upload…";
export const CORS_BLOCKED_MSG =
    "Upload blocked by browser policy. The operator must redeploy with the ALB origin (see runbook).";

export function isPresignedUnavailable(err) {
    return err?.response?.status === 501;
}

export function uploadErrorCopy(err) {
    const status = err?.response?.status;
    if (status === 409) return MISSING_OBJECT_MSG;
    if (status === 413) return OVERSIZE_MSG;
    if (err?.status !== undefined && !err?.response) return CORS_BLOCKED_MSG;
    return err?.response?.data?.detail || "Upload failed";
}

/** Audio source decision: presigned first, blob fallback on 501/403/404. */
export function shouldFallbackAudio(err) {
    const status = err?.response?.status;
    return status === 501 || status === 403 || status === 404;
}
