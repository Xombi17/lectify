import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

describe("api client base URL configuration", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv };
    delete process.env.NEXT_PUBLIC_API_BASE;
    delete process.env.NEXT_PUBLIC_BACKEND_URL;
    delete process.env.REACT_APP_BACKEND_URL;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("defaults API to relative /api when no env vars are set", async () => {
    const { API, api } = await import("../api");
    expect(API).toBe("/api");
    expect(api.defaults.baseURL).toBe("/api");
    expect(API).not.toContain("undefined");
  });

  it("never contains 'undefined' when legacy env vars are empty or whitespace", async () => {
    process.env.NEXT_PUBLIC_BACKEND_URL = "   ";
    process.env.REACT_APP_BACKEND_URL = "";
    const { API, api } = await import("../api");
    expect(API).toBe("/api");
    expect(api.defaults.baseURL).toBe("/api");
    expect(API).not.toContain("undefined");
  });

  it("allows NEXT_PUBLIC_API_BASE override if non-empty trimmed string is provided", async () => {
    process.env.NEXT_PUBLIC_API_BASE = "https://custom.backend.internal/api";
    const { API, api } = await import("../api");
    expect(API).toBe("https://custom.backend.internal/api");
    expect(api.defaults.baseURL).toBe("https://custom.backend.internal/api");
  });

  it("falls back to /api if NEXT_PUBLIC_API_BASE is only whitespace", async () => {
    process.env.NEXT_PUBLIC_API_BASE = "   ";
    const { API, api } = await import("../api");
    expect(API).toBe("/api");
    expect(api.defaults.baseURL).toBe("/api");
  });
});
