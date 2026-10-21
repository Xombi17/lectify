import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PenPlayer from "@/components/PenPlayer";

function setup(props = {}, duration = 100) {
    render(<PenPlayer src="x.mp3" {...props} />);
    const audio = screen.getByTestId("lecture-audio");
    Object.defineProperty(audio, "duration", { value: duration, configurable: true });
    fireEvent.loadedMetadata(audio);
    return audio;
}

describe("PenPlayer resume + progress", () => {
    it("resumes from startAt once metadata loads", () => {
        const audio = setup({ startAt: 42 });
        expect(audio.currentTime).toBe(42);
    });

    it("ignores a resume point in the first seconds or the last seconds", () => {
        expect(setup({ startAt: 3 }).currentTime).toBe(0);
        document.body.innerHTML = "";
        expect(setup({ startAt: 97 }, 100).currentTime).toBe(0);
    });

    it("reports progress about every 5 seconds, not on every tick", () => {
        const onProgress = vi.fn();
        const audio = setup({ onProgress });
        for (const t of [1, 2, 4]) {
            audio.currentTime = t;
            fireEvent.timeUpdate(audio);
        }
        expect(onProgress).not.toHaveBeenCalled();
        audio.currentTime = 6;
        fireEvent.timeUpdate(audio);
        expect(onProgress).toHaveBeenCalledTimes(1);
        expect(onProgress).toHaveBeenLastCalledWith(6);
    });

    it("reports the position on pause and resets to 0 when the lecture ends", () => {
        const onProgress = vi.fn();
        const audio = setup({ onProgress });
        audio.currentTime = 33;
        fireEvent.pause(audio);
        expect(onProgress).toHaveBeenLastCalledWith(33);
        fireEvent.ended(audio);
        expect(onProgress).toHaveBeenLastCalledWith(0);
    });

    it("works with no callbacks at all", () => {
        const audio = setup();
        audio.currentTime = 10;
        expect(() => {
            fireEvent.timeUpdate(audio);
            fireEvent.pause(audio);
            fireEvent.ended(audio);
        }).not.toThrow();
    });
});
