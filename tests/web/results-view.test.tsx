import { render, screen } from "@testing-library/react";

import { ResultsView } from "../../apps/web/components/results-view";

describe("ResultsView", () => {
  it("renders summaries when they are available", () => {
    render(
      <ResultsView
        topicId="topic-1"
        summaries={[
          {
            group_id: "group-1",
            content: "- One summary",
            created_at: "2026-04-23T10:00:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByText("Group 1")).toBeInTheDocument();
    expect(screen.getByText("- One summary")).toBeInTheDocument();
  });

  it("renders the empty state when no summaries exist", () => {
    render(<ResultsView topicId="topic-1" summaries={[]} />);

    expect(screen.getByRole("heading", { name: "No summaries yet" })).toBeInTheDocument();
  });
});
