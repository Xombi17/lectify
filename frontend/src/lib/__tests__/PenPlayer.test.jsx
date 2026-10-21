import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PenPlayer from "@/components/PenPlayer";

function setup() {
    const play = vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(function () {
        fireEvent.play(this);
        return Promise.resolve();
    });
    const pause = vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(function () {
        fireEvent.pause(this);
    });
    render(<PenPlayer src="x.mp3" />);
    const audio = screen.getByTestId("lecture-audio");
    Object.defineProperty(audio, "duration", { value: 100, configurable: true });
    fireEvent.loadedMetadata(audio);
    return { audio, play, pause };
}

describe("PenPlayer", () => {
    it("toggles play/pause with label", () => {
        const { play, pause } = setup();
        const btn = screen.getByTestId("pen-play-btn");
        expect(btn.getAttribute("aria-label")).toBe("Play");
        fireEvent.click(btn);
        expect(play).toHaveBeenCalled();
        expect(btn.getAttribute("aria-label")).toBe("Pause");
        fireEvent.click(btn);
        expect(pause).toHaveBeenCalled();
    });

    it("slider aria and keyboard seek", () => {
        const { audio } = setup();
        const s = screen.getByRole("slider", { name: "Seek" });
        expect(s.getAttribute("aria-valuemax")).toBe("100");
        expect(s.getAttribute("aria-valuetext")).toBe("0:00 of 1:40");
        fireEvent.keyDown(s, { key: "ArrowRight" });
        expect(audio.currentTime).toBe(5);
        fireEvent.keyDown(s, { key: "ArrowLeft" });
        fireEvent.keyDown(s, { key: "ArrowLeft" });
        expect(audio.currentTime).toBe(0);
        fireEvent.keyDown(s, { key: "End" });
        expect(audio.currentTime).toBe(100);
        fireEvent.keyDown(s, { key: "Home" });
        expect(audio.currentTime).toBe(0);
    });
});
