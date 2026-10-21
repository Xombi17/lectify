// Per-user, per-browser study state: recently opened lectures, audio resume position, and the
// "new since your last visit" marker. Pure convenience data, so every storage access is guarded
// (private windows and blocked storage must never break a page).
const MAX_RECENT = 8;

const key = (name, userId) => `lm_${name}:${userId || "anon"}`;

function read(k, fallback) {
    try {
        const raw = localStorage.getItem(k);
        return raw ? JSON.parse(raw) : fallback;
    } catch {
        return fallback;
    }
}

function write(k, value) {
    try {
        localStorage.setItem(k, JSON.stringify(value));
    } catch {
        // storage unavailable: skip silently
    }
}

export function getRecent(userId) {
    const rows = read(key("recent", userId), []);
    return Array.isArray(rows) ? rows : [];
}

export function rememberLecture(userId, { id, title, subject }) {
    const all = getRecent(userId);
    const prev = all.find((r) => r.id === id);
    const rest = all.filter((r) => r.id !== id);
    write(key("recent", userId), [{ id, title, subject, at: Date.now(), pos: prev?.pos || 0 }, ...rest].slice(0, MAX_RECENT));
}

export function savePosition(userId, id, seconds) {
    const all = getRecent(userId);
    if (!all.some((r) => r.id === id)) return;
    write(key("recent", userId), all.map((r) => (r.id === id ? { ...r, pos: Math.max(0, Math.floor(seconds)) } : r)));
}

export function getPosition(userId, id) {
    return getRecent(userId).find((r) => r.id === id)?.pos || 0;
}

export function getLastSeen(userId) {
    return Number(read(key("library_seen", userId), 0)) || 0;
}

export function markLibrarySeen(userId) {
    write(key("library_seen", userId), Date.now());
}

export const fmtClock = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
