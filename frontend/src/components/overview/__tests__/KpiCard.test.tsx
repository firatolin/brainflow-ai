import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { KpiCard } from "@/components/overview/KpiCard";

describe("KpiCard", () => {
  it("renders label, value, hint", () => {
    render(<KpiCard label="Active deliveries" value={40} hint="43 total" />);
    expect(screen.getByText("Active deliveries")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(screen.getByText("43 total")).toBeInTheDocument();
  });

  it("applies warning tone class", () => {
    render(<KpiCard label="At risk" value={12} tone="warning" />);
    const value = screen.getByText("12");
    expect(value.className).toContain("text-amber-700");
  });
});
