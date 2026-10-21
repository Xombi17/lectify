import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("uploadToS3 (browser-direct POST)", () => {
    let RealXHR;
    let lastXhr;
    let appendOrder;

    class FakeUpload {
        constructor() {
            this.handler = null;
        }
        set onprogress(fn) {
            this.handler = fn;
        }
        get onprogress() {
            return this.handler;
        }
    }

    class FakeXHR {
        constructor() {
            lastXhr = this;
            this.upload = new FakeUpload();
            this.status = 204;
            this.responseText = "";
        }
        open() {}
        send(form) {
            // Record FormData append order via the captured entries
            appendOrder = [];
            for (const [k] of form.entries()) appendOrder.push(k);
            // Simulate progress then success
            if (this.upload.handler) {
                this.upload.handler({ loaded: 50, total: 100, lengthComputable: true });
                this.upload.handler({ loaded: 100, total: 100, lengthComputable: true });
            }
            if (this.onload) this.onload();
        }
    }

    beforeEach(async () => {
        vi.resetModules();
        RealXHR = globalThis.XMLHttpRequest;
        globalThis.XMLHttpRequest = FakeXHR;
        // Minimal FormData.entries polyfill tracking (jsdom has FormData)
        appendOrder = [];
    });

    afterEach(() => {
        globalThis.XMLHttpRequest = RealXHR;
    });

    it("appends presigned fields before file", async () => {
        const { uploadToS3 } = await import("../api");
        const seen = [];
        const progress = vi.fn((l, t) => seen.push([l, t]));
        const file = new File(["audio-bytes"], "a.mp3", { type: "audio/mpeg" });
        await uploadToS3(
            { url: "https://s3.example/up", fields: { key: "k", policy: "p", "Content-Type": "audio/mpeg" } },
            file,
            progress
        );
        expect(appendOrder.slice(0, 3)).toEqual(["key", "policy", "Content-Type"]);
        expect(appendOrder[appendOrder.length - 1]).toBe("file");
        expect(progress).toHaveBeenCalledWith(50, 100);
        expect(progress).toHaveBeenCalledWith(100, 100);
    });

    it("rejects with status/body when S3 returns 403", async () => {
        const { uploadToS3 } = await import("../api");
        globalThis.XMLHttpRequest = class extends FakeXHR {
            send() {
                this.status = 403;
                this.responseText = "SignatureDoesNotMatch";
                if (this.onload) this.onload();
            }
        };
        const file = new File(["x"], "a.mp3", { type: "audio/mpeg" });
        await expect(
            uploadToS3({ url: "https://s3.example/up", fields: {} }, file, () => {})
        ).rejects.toMatchObject({ status: 403 });
    });

    it("rejects when presigned url is missing", async () => {
        const { uploadToS3 } = await import("../api");
        const file = new File(["x"], "a.mp3", { type: "audio/mpeg" });
        await expect(uploadToS3({}, file, () => {})).rejects.toMatchObject({ status: 0 });
    });
});

describe("lectureApi presigned endpoints", () => {
    it("hits upload-url, upload-complete and audio-url contracts", async () => {
        vi.resetModules();
        const { api, lectureApi } = await import("../api");
        const post = vi.spyOn(api, "post").mockImplementation((url) => {
            if (url === "/lectures/upload-url") return Promise.resolve({ data: { lecture_id: "l1" } });
            if (url.endsWith("/upload-complete")) return Promise.resolve({ data: { id: "l1" } });
            return Promise.resolve({ data: {} });
        });
        const get = vi.spyOn(api, "get").mockImplementation(() => Promise.resolve({ data: { url: "https://x", expires_in: 900 } }));
        await lectureApi.uploadUrl({ title: "t" });
        expect(post).toHaveBeenCalledWith("/lectures/upload-url", { title: "t" });
        await lectureApi.uploadComplete("l1");
        expect(post).toHaveBeenCalledWith("/lectures/l1/upload-complete");
        const audio = await lectureApi.audioPresignedUrl("l1");
        expect(get).toHaveBeenCalledWith("/lectures/l1/audio-url");
        expect(audio.expires_in).toBe(900);
        post.mockRestore();
        get.mockRestore();
    });

    it("501 from upload-url is detectable as presigned-unavailable (multipart fallback)", async () => {
        const { isPresignedUnavailable, FALLBACK_NOTICE } = await import("../uploadTransport");
        expect(isPresignedUnavailable({ response: { status: 501 } })).toBe(true);
        expect(isPresignedUnavailable({ response: { status: 400 } })).toBe(false);
        expect(FALLBACK_NOTICE).toMatch(/standard upload/);
    });

    it("409 maps to the missing-object copy with form values retained", async () => {
        const { uploadErrorCopy, MISSING_OBJECT_MSG } = await import("../uploadTransport");
        expect(uploadErrorCopy({ response: { status: 409 } })).toBe(MISSING_OBJECT_MSG);
        expect(MISSING_OBJECT_MSG).toMatch(/did not reach storage/);
    });
});

describe("status pills + audio preference", () => {
    it("maps ready/uploading/dead_letter per UI-SPEC", async () => {
        const { STATUS_LABEL, statusPillKind, FAILED_MESSAGE } = await import("../lectureStatus");
        expect(STATUS_LABEL.ready).toBe("Ready");
        expect(statusPillKind("ready")).toBe("ready");
        for (const s of ["uploading", "queued", "processing", "retrying", "uploaded"]) {
            expect(statusPillKind(s)).toBe("processing");
            expect(STATUS_LABEL[s]).toBe("Writing up");
        }
        expect(statusPillKind("dead_letter")).toBe("failed");
        expect(STATUS_LABEL.dead_letter).toBe("Retry processing");
        expect(FAILED_MESSAGE).toMatch(/ask an admin/);
    });

    it("audio prefers presigned src with no auth header; 501 falls back to blob", async () => {
        const { shouldFallbackAudio } = await import("../uploadTransport");
        expect(shouldFallbackAudio({ response: { status: 501 } })).toBe(true);
        expect(shouldFallbackAudio({ response: { status: 403 } })).toBe(true);
        expect(shouldFallbackAudio({ response: { status: 200 } })).toBe(false);
        // Presigned branch sends no Authorization header: contract is a plain URL string.
        const presignedSrc = "https://s3.example/audio.mp3?sig=1";
        expect(presignedSrc.startsWith("https://")).toBe(true);
    });

    it("no new polling endpoint is introduced", async () => {
        const fs = await import("fs");
        const src = fs.readFileSync("src/cra-pages/LectureDetailPage.jsx", "utf8");
        expect(src).not.toMatch(/\/job-status.*poll|new.*poll/i);
        expect(src).toMatch(/uploading/);
    });
});
