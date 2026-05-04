import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { AdminDashboardView } from "../../apps/web/components/admin-dashboard";

describe("AdminDashboardView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the protected admin shell", () => {
    render(<AdminDashboardView apiBaseUrl="https://api.example.com" />);

    expect(screen.getByText("Admin dashboard")).toBeInTheDocument();
    expect(screen.getByLabelText("Admin key")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load dashboard" })).toBeInTheDocument();
  });

  it("hides the admin key field after a saved key loads the dashboard", async () => {
    vi.stubGlobal("fetch", async () => ({
      ok: true,
      json: async () => ({
        topics: [],
        active_topic_id: null,
        generated_at: "2026-05-01T10:00:00Z",
      }),
    }));
    vi.stubGlobal("localStorage", {
      getItem: () => "admin-key",
      removeItem: () => undefined,
      setItem: () => undefined,
    });

    render(<AdminDashboardView apiBaseUrl="https://api.example.com" />);

    expect(await screen.findByRole("button", { name: "Sign out" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByLabelText("Admin key")).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Refresh dashboard" })).toBeInTheDocument();
    expect(screen.queryByText("Admin session active")).not.toBeInTheDocument();
  });

  it("keeps topic creation and end-date controls collapsed by default", async () => {
    vi.stubGlobal("fetch", async () => ({
      ok: true,
      json: async () => ({
        topics: [
          {
            topic: {
              id: "active-topic",
              title: "Active topic",
              description: null,
              closes_at: "2026-05-10T10:00:00Z",
              status: "active",
              created_at: "2026-05-01T10:00:00Z",
            },
            groups: [],
            participant_count: 0,
            message_count: 0,
            summary_count: 0,
          },
          {
            topic: {
              id: "closed-topic",
              title: "Closed topic",
              description: null,
              closes_at: "2026-05-02T10:00:00Z",
              status: "closed",
              created_at: "2026-04-01T10:00:00Z",
            },
            groups: [],
            participant_count: 0,
            message_count: 0,
            summary_count: 0,
          },
        ],
        active_topic_id: "active-topic",
        generated_at: "2026-05-01T10:00:00Z",
      }),
    }));
    vi.stubGlobal("localStorage", {
      getItem: () => "admin-key",
      removeItem: () => undefined,
      setItem: () => undefined,
    });

    render(<AdminDashboardView apiBaseUrl="https://api.example.com" />);

    expect(await screen.findByText("Active topic")).toBeInTheDocument();
    expect(screen.getByText("Past topics")).toBeInTheDocument();
    expect(screen.getByText(/^Ended:/)).toBeInTheDocument();
    expect(screen.queryByPlaceholderText("Topic title")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Deliberation end in your timezone")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "+ add topic" }));

    expect(screen.getByPlaceholderText("Topic title")).toBeInTheDocument();
    expect(screen.getByLabelText("Deliberation end in your timezone")).toHaveAttribute("min");
  });

  it("uses an in-place future-only end date editor for active topics", async () => {
    vi.stubGlobal("fetch", async () => ({
      ok: true,
      json: async () => ({
        topics: [
          {
            topic: {
              id: "active-topic",
              title: "Active topic",
              description: null,
              closes_at: "2026-05-10T10:00:00Z",
              status: "active",
              created_at: "2026-05-01T10:00:00Z",
            },
            groups: [],
            participant_count: 0,
            message_count: 0,
            summary_count: 0,
          },
        ],
        active_topic_id: "active-topic",
        generated_at: "2026-05-01T10:00:00Z",
      }),
    }));
    vi.stubGlobal("localStorage", {
      getItem: () => "admin-key",
      removeItem: () => undefined,
      setItem: () => undefined,
    });

    render(<AdminDashboardView apiBaseUrl="https://api.example.com" />);

    const editButton = await screen.findByRole("button", { name: /Edit deliberation end/ });

    expect(screen.getByText("edit")).toBeInTheDocument();
    fireEvent.click(editButton);
    expect(screen.getByLabelText("Expected end")).toHaveAttribute("min");
  });

  it("asks for confirmation before changing an end date", async () => {
    vi.stubGlobal("fetch", async () => ({
      ok: true,
      json: async () => ({
        topics: [
          {
            topic: {
              id: "active-topic",
              title: "Active topic",
              description: null,
              closes_at: "2026-05-10T10:00:00Z",
              status: "active",
              created_at: "2026-05-01T10:00:00Z",
            },
            groups: [],
            participant_count: 0,
            message_count: 0,
            summary_count: 0,
          },
        ],
        active_topic_id: "active-topic",
        generated_at: "2026-05-01T10:00:00Z",
      }),
    }));
    vi.stubGlobal("localStorage", {
      getItem: () => "admin-key",
      removeItem: () => undefined,
      setItem: () => undefined,
    });

    render(<AdminDashboardView apiBaseUrl="https://api.example.com" />);

    fireEvent.click(await screen.findByRole("button", { name: /Edit deliberation end/ }));
    const endInput = screen.getByLabelText("Expected end");
    fireEvent.change(endInput, { target: { value: "2026-05-12T10:00" } });
    fireEvent.blur(endInput);

    expect(screen.getByRole("dialog")).toHaveTextContent("Change end date?");
    expect(screen.getByRole("button", { name: "Change date" })).toBeInTheDocument();
  });

  it("asks for confirmation before creating a topic while one is active", async () => {
    vi.stubGlobal("fetch", async () => ({
      ok: true,
      json: async () => ({
        topics: [
          {
            topic: {
              id: "active-topic",
              title: "Active topic",
              description: null,
              closes_at: "2026-05-10T10:00:00Z",
              status: "active",
              created_at: "2026-05-01T10:00:00Z",
            },
            groups: [],
            participant_count: 0,
            message_count: 0,
            summary_count: 0,
          },
        ],
        active_topic_id: "active-topic",
        generated_at: "2026-05-01T10:00:00Z",
      }),
    }));
    vi.stubGlobal("localStorage", {
      getItem: () => "admin-key",
      removeItem: () => undefined,
      setItem: () => undefined,
    });

    render(<AdminDashboardView apiBaseUrl="https://api.example.com" />);

    fireEvent.click(await screen.findByRole("button", { name: "+ add topic" }));
    fireEvent.change(screen.getByPlaceholderText("Topic title"), {
      target: { value: "Replacement topic" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create" }));

    expect(screen.getByRole("dialog")).toHaveTextContent("Replace active topic?");
    expect(screen.getByRole("button", { name: "Create topic" })).toBeInTheDocument();
  });
});
