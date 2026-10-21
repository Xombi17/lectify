import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const css = fs.readFileSync(path.resolve(__dirname, "../../index.css"), "utf8");

// Literal primitives every theme block must define (H S% L% triplets).
const PRIMITIVES = [
  "canvas", "surface", "surface-2", "surface-3", "hairline", "hairline-strong", "ink", "body", "muted-ink",
  "accent-ink", "on-accent", "accent-brand", "accent-wash", "accent-wash-fg", "warn", "danger", "on-danger",
  "hl-mark", "shadow", "shadow-float",
];
// Semantic + legacy names: defined once in :root as var() aliases so every theme inherits them.
const ALIASES = [
  "background", "foreground", "card", "card-foreground", "popover", "popover-foreground",
  "primary", "primary-foreground", "secondary", "secondary-foreground", "muted", "muted-foreground",
  "accent", "accent-foreground", "destructive", "destructive-foreground", "border", "input", "ring",
  "desk", "paper", "paper-2", "line", "line-strong", "margin", "ink-soft", "pen", "pen-fg",
  "hl", "hl-fg", "hl-mark-fg", "amber", "red", "tape",
];

function block(selector) {
  const i = css.indexOf(selector + " {");
  if (i < 0) return "";
  const start = css.indexOf("{", i) + 1;
  return css.slice(start, css.indexOf("}", start));
}

const blocks = {
  day: block(":root"),
  fallback: block(':root:not([data-theme="light"])'),
  dark: block(':root[data-theme="dark"]'),
};

function vars(b) {
  const out = {};
  for (const m of b.matchAll(/--([a-z0-9-]+):\s*([^;]+);/g)) out[m[1]] = m[2].trim();
  return out;
}

function rgb(v) {
  const m = v.match(/^([\d.]+)\s+([\d.]+)%\s+([\d.]+)%$/);
  if (!m) throw new Error(`not an hsl triplet: ${v}`);
  const h = +m[1], s = +m[2] / 100, l = +m[3] / 100;
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  return [0, 8, 4].map((n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1))));
}
function lum(v) {
  const [r, g, b] = rgb(v).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function ratio(a, b) {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

// Text pairs: WCAG AA 4.5:1.
const PAIRS = [
  ["ink", "canvas"], ["ink", "surface"], ["body", "canvas"], ["muted-ink", "canvas"], ["muted-ink", "surface"],
  ["muted-ink", "surface-2"], ["muted-ink", "surface-3"], ["accent-ink", "canvas"], ["accent-ink", "surface"],
  ["accent-ink", "surface-2"], ["on-accent", "accent-ink"], ["accent-wash-fg", "accent-wash"],
  ["warn", "surface"], ["warn", "canvas"], ["danger", "surface"], ["danger", "canvas"], ["on-danger", "danger"],
];
// UI component / focus-ring pairs: WCAG 1.4.11 3:1.
const UI_PAIRS = [["hairline-strong", "canvas"], ["hairline-strong", "surface"], ["accent-ink", "surface-2"]];

describe("Editorial warm tokens", () => {
  it("old lime, notebook-blue and the .dark block are gone", () => {
    expect(css).not.toContain("70 100% 50%");
    expect(css).not.toContain("226.0 65.2% 34.9%");
    expect(css).not.toMatch(/\.dark\s*\{/);
  });

  it(":root defines every semantic and legacy alias", () => {
    const v = vars(blocks.day);
    expect(ALIASES.filter((k) => !(k in v))).toEqual([]);
  });

  for (const [name, b] of Object.entries(blocks)) {
    describe(name, () => {
      const v = vars(b);
      it("defines every primitive", () => {
        expect(b).not.toBe("");
        expect(PRIMITIVES.filter((k) => !(k in v))).toEqual([]);
      });
      it.each(PAIRS)("text contrast %s on %s >= 4.5", (fg, bg) => {
        expect(ratio(v[fg], v[bg])).toBeGreaterThanOrEqual(4.5);
      });
      it.each(UI_PAIRS)("UI contrast %s on %s >= 3", (fg, bg) => {
        expect(ratio(v[fg], v[bg])).toBeGreaterThanOrEqual(3);
      });
    });
  }
});
