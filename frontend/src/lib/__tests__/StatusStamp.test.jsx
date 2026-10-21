import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusStamp from "@/components/StatusStamp";

describe("StatusStamp", () => {
    it.each([
        ["ready", "ready", "stamp-ready", "Ready"],
        ["queued", "processing", "stamp-proc", "Writing up"],
        ["dead_letter", "failed", "stamp-fail", "Retry processing"],
        ["weird", "processing", "stamp-proc", "Writing up"],
    ])("%s", (status, kind, cls, text) => {
        render(<StatusStamp status={status} />);
        const el = screen.getByTestId("status-badge");
        expect(el.dataset.kind).toBe(kind);
        expect(el.className).toContain(cls);
        expect(el.textContent).toBe(text);
    });
});
