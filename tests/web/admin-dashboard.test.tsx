import { render, screen } from "@testing-library/react";

import { AdminDashboardView } from "../../apps/web/components/admin-dashboard";

describe("AdminDashboardView", () => {
  it("renders the protected admin shell", () => {
    render(<AdminDashboardView apiBaseUrl="https://api.example.com" />);

    expect(screen.getByRole("heading", { name: "Operate CORDA" })).toBeInTheDocument();
    expect(screen.getByLabelText("Admin key")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load dashboard" })).toBeInTheDocument();
  });
});
