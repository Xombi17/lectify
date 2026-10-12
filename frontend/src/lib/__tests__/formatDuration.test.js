import { describe, it, expect } from "vitest";
import { formatProcessing } from "../formatDuration";

describe("formatProcessing", () => {
  it("formats seconds and minutes", () => {
    expect(formatProcessing(12.4)).toBe("12.4 s");
    expect(formatProcessing(65)).toBe("1m 05s");
    expect(formatProcessing(null)).toBeNull();
  });
});
