import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";

// Fast compile/syntax gate: every page and feature component must import.
const root = path.resolve(__dirname, "../..");
const SKIP = [];
const files = ["cra-pages", "components"].flatMap((d) =>
  fs.readdirSync(path.join(root, d)).filter((f) => f.endsWith(".jsx") && !SKIP.includes(f)).map((f) => [d, f]),
);

describe("modules import", () => {
  it.each(files)("%s/%s", async (d, f) => {
    const mod = await import(`../../${d}/${f}`);
    expect(mod.default).toBeDefined();
  });
});
