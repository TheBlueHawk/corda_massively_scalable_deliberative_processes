import { ErrorState } from "@/components/error-state";
import { AdminDashboardView } from "@/components/admin-dashboard";

export default function AdminPage() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!apiBaseUrl) {
    return (
      <ErrorState
        title="Admin unavailable"
        detail="Missing NEXT_PUBLIC_API_BASE_URL environment variable."
      />
    );
  }
  return <AdminDashboardView apiBaseUrl={apiBaseUrl} />;
}
