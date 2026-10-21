import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

const ROOTS = [path.resolve(__dirname, "../.."), path.resolve(__dirname, "../../../app")];

function walk(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const f = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name !== "__tests__" && e.name !== "node_modules") walk(f, out);
    } else if (/\.(jsx?|tsx?|css)$/.test(e.name)) out.push(f);
  }
  return out;
}

const files = ROOTS.flatMap((r) => walk(r)).map((f) => [f, fs.readFileSync(f, "utf8")]);
const BANNED = ["70 100% 50%", "Cabinet Grotesk", "IBM Plex", "JetBrains Mono", "fonts.googleapis", "api.fontshare", "unpkg.com", "Bricolage", "Caveat", "--font-hand)"];

describe("design guards", () => {
  it.each(BANNED)("no %s", (s) => {
    expect(files.filter(([, c]) => c.includes(s)).map(([f]) => f)).toEqual([]);
  });
  it("no standalone text-accent outside components/ui", () => {
    const bad = files
      .filter(([f]) => !f.includes(`components${path.sep}ui${path.sep}`))
      .filter(([, c]) => /text-accent(?!-foreground)/.test(c))
      .map(([f]) => f);
    expect(bad).toEqual([]);
  });
});

function listTop(dir, re) {
  return fs.existsSync(dir)
    ? fs.readdirSync(dir, { withFileTypes: true }).filter((e) => e.isFile() && re.test(e.name)).map((e) => path.join(dir, e.name))
    : [];
}
function walkTsx(dir, out = []) {
  if (!fs.existsSync(dir)) return out;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const f = path.join(dir, e.name);
    if (e.isDirectory()) walkTsx(f, out);
    else if (/\.tsx$/.test(e.name)) out.push(f);
  }
  return out;
}
const SRC = path.resolve(__dirname, "../..");
const surface = [
  ...listTop(path.join(SRC, "cra-pages"), /\.jsx$/),
  ...listTop(path.join(SRC, "components"), /\.jsx$/),
  ...walkTsx(path.resolve(SRC, "../app")),
].map((f) => [f, fs.readFileSync(f, "utf8")]);

const RULES = {
  // Editorial contract: weights 400/500 only (font-bold is remapped to 500 in tailwind.config.js).
  weights: /font-(semibold|extrabold|black|light|thin)\b/,
  // Scale: caption 13-14 (sm) / body 16 (base) / title 18-24 (lg, xl, 2xl) / display via clamp() classes.
  sizes: /\btext-(xs|[3-9]xl)\b/,
  arbitrarySize: /text-\[[0-9.]+(px|rem)\]/,
  palette: /\b(amber|red|green|yellow|emerald|lime|zinc|gray|slate|blue|indigo)-[0-9]{2,3}\b/,
  duotone: /duotone/,
  textWhite: /text-white\b/,
  textAccent: /text-accent(?!-foreground)/,
  darkVariant: /\bdark:/,
};

describe("design contract (surfaces)", () => {
  it.each(Object.entries(RULES))("no %s", (_name, re) => {
    const bad = surface
      .map(([f, c]) => [path.relative(SRC, f), c.match(re)?.[0]])
      .filter(([, m]) => m)
      .map(([f, m]) => `${f}: ${m}`);
    expect(bad).toEqual([]);
  });
  it("framer-motion users honour useReducedMotion", () => {
    const bad = surface
      .filter(([, c]) => c.includes("framer-motion") && !c.includes("useReducedMotion"))
      .map(([f]) => path.relative(SRC, f));
    expect(bad).toEqual([]);
  });
  it("font-bold renders at 500 and only Inter + Newsreader (+ mono) are loaded", () => {
    const tw = fs.readFileSync(path.resolve(SRC, "../tailwind.config.js"), "utf8");
    expect(tw).toMatch(/bold:\s*'500'/);
    const c = fs.readFileSync(path.resolve(SRC, "../app/layout.tsx"), "utf8");
    const fonts = c.match(/import \{([^}]+)\} from "next\/font\/google"/)[1].split(",").map((x) => x.trim()).sort();
    expect(fonts).toEqual(["Geist_Mono", "Inter", "Newsreader"]);
  });
  it("layout has pre-paint theme wiring", () => {
    const c = fs.readFileSync(path.resolve(SRC, "../app/layout.tsx"), "utf8");
    expect(c).toContain("suppressHydrationWarning");
    expect(c).toContain("lectify-theme");
  });
});

describe("icon guard", () => {
  it("no @phosphor-icons/react or lucide-react imports (use @/components/icons)", () => {
    const re = /(from|import|require\()\s*["'](@phosphor-icons\/react|lucide-react)["']/;
    const bad = ROOTS.flatMap((r) => walk(r))
      .filter((f) => re.test(fs.readFileSync(f, "utf8")))
      .map((f) => path.relative(SRC, f));
    expect(bad).toEqual([]);
  });
});
