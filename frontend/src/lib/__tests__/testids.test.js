import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import baseline from "./testids.baseline.json";

const SRC = path.resolve(__dirname, "../..");

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const f = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name !== "__tests__" && e.name !== "node_modules") walk(f, out);
    } else if (/\.(jsx?|tsx?)$/.test(e.name)) out.push(f);
  }
  return out;
}

describe("data-testid preservation", () => {
  const all = walk(SRC).map((f) => fs.readFileSync(f, "utf8")).join("\n");
  it("baseline is non-empty", () => expect(baseline.length).toBeGreaterThan(50));
  it.each(baseline)("still present: %s", (id) => {
    expect(all.includes(`data-testid="${id}"`) || all.includes("data-testid={`" + id + "`}")).toBe(true);
  });
});
