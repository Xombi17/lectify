import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { GET } from "../../../app/healthz/route";
import { middleware } from "../../../middleware";

describe("/healthz route and middleware exemption", () => {
  it("returns 200 { status: 'ok' } with cache-control: no-store from GET handler", async () => {
    const response = await GET();
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body).toEqual({ status: "ok" });
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  it("passes through middleware without authentication redirect", () => {
    const request = new NextRequest("http://localhost:3000/healthz");
    const response = middleware(request);
    
    // If not redirected, response status will not be 307 or 308 (redirect)
    // Next.js NextResponse.next() sets x-middleware-next header
    expect(response.headers.get("location")).toBeNull();
    expect(response.status).toBe(200);
  });
});
