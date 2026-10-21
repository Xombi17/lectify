import { describe, it, expect } from "vitest";
import { extractResetToken } from "@/cra-pages/ForgotPasswordPage";

describe("extractResetToken", () => {
    it("pulls the token out of a full pasted link", () => {
        expect(extractResetToken("http://lectify.example.edu/reset-password?token=abc.def.ghi")).toBe("abc.def.ghi");
    });

    it("pulls it out of a path-only link", () => {
        expect(extractResetToken("/reset-password?token=abc123")).toBe("abc123");
    });

    it("accepts a bare token and trims whitespace", () => {
        expect(extractResetToken("  abc.def.ghi \n")).toBe("abc.def.ghi");
    });

    it("returns an empty string for blank input", () => {
        expect(extractResetToken("")).toBe("");
        expect(extractResetToken("   ")).toBe("");
        expect(extractResetToken(undefined)).toBe("");
    });
});
