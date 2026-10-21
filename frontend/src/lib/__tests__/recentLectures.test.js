import { describe, it, expect, beforeEach, vi } from "vitest";
import {
    fmtClock,
    getLastSeen,
    getPosition,
    getRecent,
    markLibrarySeen,
    rememberLecture,
    savePosition,
} from "@/lib/recentLectures";

const lec = (n) => ({ id: `lec${n}`, title: `Lecture ${n}`, subject: "OS" });

describe("recentLectures", () => {
    beforeEach(() => localStorage.clear());

    it("remembers lectures most-recent-first without duplicates", () => {
        rememberLecture("u1", lec(1));
        rememberLecture("u1", lec(2));
        rememberLecture("u1", lec(1));
        expect(getRecent("u1").map((r) => r.id)).toEqual(["lec1", "lec2"]);
    });

    it("keeps at most 8 entries", () => {
        for (let i = 0; i < 12; i++) rememberLecture("u1", lec(i));
        const ids = getRecent("u1").map((r) => r.id);
        expect(ids).toHaveLength(8);
        expect(ids[0]).toBe("lec11");
    });

    it("saves and returns the audio position, and keeps it when the lecture is reopened", () => {
        rememberLecture("u1", lec(1));
        savePosition("u1", "lec1", 125.9);
        expect(getPosition("u1", "lec1")).toBe(125);
        rememberLecture("u1", lec(1));
        expect(getPosition("u1", "lec1")).toBe(125);
    });

    it("does not create an entry just by saving a position", () => {
        savePosition("u1", "ghost", 50);
        expect(getRecent("u1")).toEqual([]);
        expect(getPosition("u1", "ghost")).toBe(0);
    });

    it("keeps each user's data separate", () => {
        rememberLecture("u1", lec(1));
        expect(getRecent("u2")).toEqual([]);
    });

    it("tracks the last library visit per user", () => {
        expect(getLastSeen("u1")).toBe(0);
        markLibrarySeen("u1");
        expect(getLastSeen("u1")).toBeGreaterThan(0);
        expect(getLastSeen("u2")).toBe(0);
    });

    it("survives corrupted or unavailable storage", () => {
        localStorage.setItem("lm_recent:u1", "{not json");
        expect(getRecent("u1")).toEqual([]);
        const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
            throw new Error("quota");
        });
        expect(() => rememberLecture("u1", lec(1))).not.toThrow();
        spy.mockRestore();
    });

    it("formats a clock", () => {
        expect(fmtClock(0)).toBe("0:00");
        expect(fmtClock(65)).toBe("1:05");
        expect(fmtClock(3725)).toBe("62:05");
    });
});
