import { describe, expect, it } from "vitest";
import { getCsrfToken } from "@/lib/auth";

describe("auth helpers", () => {
  it("returns null CSRF when no cookie", () => {
    expect(getCsrfToken()).toBeNull();
  });
});
