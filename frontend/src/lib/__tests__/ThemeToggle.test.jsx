import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

const state = { resolvedTheme: "light", setTheme: vi.fn() };
vi.mock("next-themes", () => ({ useTheme: () => state }));

import ThemeToggle from "../../components/ThemeToggle";

describe("ThemeToggle", () => {
  beforeEach(() => state.setTheme.mockClear());

  it("offers dark theme in light and switches to dark", () => {
    state.resolvedTheme = "light";
    render(<ThemeToggle />);
    const btn = screen.getByTestId("theme-toggle");
    expect(btn).toHaveAttribute("aria-label", "Switch to dark theme");
    fireEvent.click(btn);
    expect(state.setTheme).toHaveBeenCalledWith("dark");
  });

  it("offers light theme in dark and switches to light", () => {
    state.resolvedTheme = "dark";
    render(<ThemeToggle />);
    const btn = screen.getByTestId("theme-toggle");
    expect(btn).toHaveAttribute("aria-label", "Switch to light theme");
    fireEvent.click(btn);
    expect(state.setTheme).toHaveBeenCalledWith("light");
  });
});
