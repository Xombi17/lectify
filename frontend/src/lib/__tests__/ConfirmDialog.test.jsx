import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ConfirmDialog from "@/components/ConfirmDialog";

function setup() {
    const onConfirm = vi.fn();
    const onOpenChange = vi.fn();
    render(<ConfirmDialog open onOpenChange={onOpenChange} title="Delete Week 3?" confirmLabel="Delete lecture" onConfirm={onConfirm} />);
    return { onConfirm, onOpenChange };
}

describe("ConfirmDialog", () => {
    it("renders alertdialog with custom labels", () => {
        setup();
        expect(screen.getByRole("alertdialog")).toBeTruthy();
        expect(screen.getByText("Delete lecture")).toBeTruthy();
        expect(screen.getByText("Keep it")).toBeTruthy();
    });
    it("confirm calls onConfirm once", () => {
        const { onConfirm } = setup();
        fireEvent.click(screen.getByText("Delete lecture"));
        expect(onConfirm).toHaveBeenCalledTimes(1);
    });
    it("cancel closes without confirming", () => {
        const { onConfirm, onOpenChange } = setup();
        fireEvent.click(screen.getByText("Keep it"));
        expect(onOpenChange).toHaveBeenCalledWith(false);
        expect(onConfirm).not.toHaveBeenCalled();
    });
});
