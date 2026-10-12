/** 12.4 -> "12.4 s", 65 -> "1m 05s" */
export function formatProcessing(sec) {
    if (sec == null || Number.isNaN(sec)) return null;
    if (sec < 60) return `${sec.toFixed(1)} s`;
    const t = Math.round(sec);
    return `${Math.floor(t / 60)}m ${String(t % 60).padStart(2, "0")}s`;
}
