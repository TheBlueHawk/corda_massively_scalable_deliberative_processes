export type ActiveTopic = {
  id: string;
  title: string;
  description: string | null;
  closes_at: string | null;
};

export type GroupSummary = {
  group_id: string;
  content: string;
  created_at: string;
};

function getApiBaseUrl(): string {
  const apiBaseUrl = process.env.PUBLIC_API_BASE_URL;
  if (!apiBaseUrl) {
    throw new Error("Missing PUBLIC_API_BASE_URL environment variable.");
  }
  return apiBaseUrl.replace(/\/$/, "");
}

export async function fetchActiveTopic(): Promise<ActiveTopic> {
  const response = await fetch(`${getApiBaseUrl()}/topics/active`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load active topic.");
  }
  return (await response.json()) as ActiveTopic;
}

export async function fetchSummaries(topicId: string): Promise<GroupSummary[]> {
  const response = await fetch(`${getApiBaseUrl()}/topics/${topicId}/summaries`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Failed to load summaries.");
  }
  return (await response.json()) as GroupSummary[];
}
