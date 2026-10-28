import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("merges class strings", () => {
    expect(cn("a", "b")).toBe("a b");
  });
  it("resolves tailwind conflicts (later wins)", () => {
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
  it("skips falsy values", () => {
    expect(cn("a", false, undefined, null, "b")).toBe("a b");
  });
});
