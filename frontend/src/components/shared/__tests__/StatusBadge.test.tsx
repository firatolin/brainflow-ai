import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  DeliveryStatusBadge, DeliveryPriorityBadge, RiskScoreBadge, AvailableBadge,
} from "@/components/shared/StatusBadge";

describe("StatusBadge", () => {
  it("renders delivery statuses", () => {
    render(<DeliveryStatusBadge status="in_transit" />);
    expect(screen.getByText("In transit")).toBeInTheDocument();
  });

  it("renders priorities", () => {
    render(<DeliveryPriorityBadge priority="urgent" />);
    expect(screen.getByText("Urgent")).toBeInTheDocument();
  });

  it("colors risk by band", () => {
    const { rerender } = render(<RiskScoreBadge score={10} />);
    expect(screen.getByText("10")).toBeInTheDocument();
    rerender(<RiskScoreBadge score={80} />);
    expect(screen.getByText("80")).toBeInTheDocument();
  });

  it("renders availability", () => {
    render(<AvailableBadge available={false} />);
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
  });
});
