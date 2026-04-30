import { render, screen } from "@testing-library/react";

import { HomeView } from "../../apps/web/components/home-view";

describe("HomeView", () => {
  it("renders the active topic and join link", () => {
    render(
      <HomeView
        topics={[
          {
            id: "topic-1",
            title: "Climate assembly",
            description: "Discuss long-term climate measures.",
            status: "active",
            closes_at: "2026-04-23T10:00:00Z",
            created_at: "2026-04-20T10:00:00Z",
          },
        ]}
        botUsername="corda_bot"
      />,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Climate assembly" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Join a Group" })).toHaveAttribute(
      "href",
      "https://t.me/corda_bot?start=topic-1",
    );
  });

  it("renders past topics when there is no active topic", () => {
    render(
      <HomeView
        topics={[
          {
            id: "topic-1",
            title: "Cars downtown",
            description: "Should cities restrict cars?",
            status: "closed",
            closes_at: "2026-04-27T15:00:00Z",
            created_at: "2026-04-20T10:00:00Z",
          },
        ]}
        botUsername="corda_bot"
      />,
    );

    expect(screen.getByText("No active topic")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Read Latest Summary" })).toHaveAttribute(
      "href",
      "/results?topicId=topic-1",
    );
  });
});
