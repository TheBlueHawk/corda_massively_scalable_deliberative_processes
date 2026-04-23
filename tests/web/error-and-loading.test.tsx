import { render, screen } from "@testing-library/react";

import { ErrorState } from "../../apps/web/components/error-state";
import { LoadingState } from "../../apps/web/components/loading-state";

describe("UI states", () => {
  it("renders the error state", () => {
    render(<ErrorState title="Topic unavailable" detail="Failed to load the active topic." />);

    expect(screen.getByRole("heading", { name: "Topic unavailable" })).toBeInTheDocument();
  });

  it("renders the loading state", () => {
    render(<LoadingState />);

    expect(screen.getByRole("heading", { name: "Loading topic" })).toBeInTheDocument();
  });
});
