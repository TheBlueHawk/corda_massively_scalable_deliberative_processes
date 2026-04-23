import { render, screen } from "@testing-library/react";

import { HomeView } from "../../apps/web/components/home-view";

describe("HomeView", () => {
  it("renders the active topic and join link", () => {
    render(
      <HomeView
        topic={{
          id: "topic-1",
          title: "Climate assembly",
          description: "Discuss long-term climate measures.",
          closes_at: "2026-04-23T10:00:00Z",
        }}
        botUsername="corda_bot"
      />,
    );

    expect(screen.getByRole("heading", { name: "Climate assembly" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Join a Group" })).toHaveAttribute(
      "href",
      "https://t.me/corda_bot?start=topic-1",
    );
  });
});
