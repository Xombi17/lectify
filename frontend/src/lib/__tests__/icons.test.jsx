import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import * as icons from "@/components/icons";

const entries = Object.entries(icons).filter(([n]) => n !== "Icon" && n !== "default");

describe("icon set", () => {
  it("exports icons", () => expect(entries.length).toBeGreaterThan(50));
  it.each(entries)("%s renders an aria-hidden svg honoring size", (_n, C) => {
    const { container } = render(<C size={20} weight="bold" className="c" />);
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.getAttribute("width")).toBe("20");
    expect(svg.getAttribute("viewBox")).toBe("0 0 24 24");
    expect(svg.hasAttribute("weight")).toBe(false);
    expect(svg.querySelector("path,circle,rect")).toBeTruthy();
  });
  it("title makes it labelled", () => {
    const { container } = render(<icons.Check title="Done" />);
    const svg = container.querySelector("svg");
    expect(svg.getAttribute("aria-hidden")).toBeNull();
    expect(svg.getAttribute("width")).toBe("24");
  });
});
