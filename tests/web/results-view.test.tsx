import { render, screen } from "@testing-library/react";

import { ResultsView } from "../../apps/web/components/results-view";

describe("ResultsView", () => {
  it("renders summaries when they are available", () => {
    render(
      <ResultsView
        topic={{
          id: "topic-1",
          title: "Cars downtown",
          description: "Should cities restrict cars?",
          status: "closed",
          closes_at: "2026-04-27T15:00:00Z",
          cross_pollination_interval_seconds: 86400,
          next_cross_pollination_at: null,
          created_at: "2026-04-20T10:00:00Z",
        }}
        summaries={[
          {
            group_id: "group-1",
            content: "# Main points\n\n- **Agreement:** One summary",
            created_at: "2026-04-23T10:00:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Cars downtown" })).toBeInTheDocument();
    expect(screen.getByText("Summary")).toBeInTheDocument();
    expect(screen.getByText("Group 1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Main points" })).toBeInTheDocument();
    expect(screen.getByText("Agreement:")).toBeInTheDocument();
    expect(screen.getByText(/One summary/)).toBeInTheDocument();
  });

  it("renders the empty state when no summaries exist", () => {
    render(
      <ResultsView
        topic={{
          id: "topic-1",
          title: "Cars downtown",
          description: null,
          status: "closed",
          closes_at: "2026-04-27T15:00:00Z",
          cross_pollination_interval_seconds: 86400,
          next_cross_pollination_at: null,
          created_at: "2026-04-20T10:00:00Z",
        }}
        summaries={[]}
      />,
    );

    expect(screen.getByRole("heading", { name: "No summaries yet" })).toBeInTheDocument();
  });
});
