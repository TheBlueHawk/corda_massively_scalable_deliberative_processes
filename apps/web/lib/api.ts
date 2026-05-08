export type ActiveTopic = {
  id: string;
  title: string;
  description: string | null;
  closes_at: string | null;
};

export type TopicStatus = "active" | "closed";

export type TopicListItem = ActiveTopic & {
  status: TopicStatus;
  cross_pollination_interval_seconds: number;
  next_cross_pollination_at: string | null;
  group_capacity: number;
  seed_bullets?: string[];
  created_at: string;
};

export type GroupSummary = {
  group_id: string;
  content: string;
  created_at: string;
};

export type AdminGroupOverview = {
  id: string;
  topic_id: string;
  thread_id: number;
  invite_link: string;
  capacity: number;
  member_count: number;
  telegram_topic_name: string;
  message_count: number;
  has_summary: boolean;
  summary_created_at: string | null;
};

export type AdminTopicOverview = {
  topic: TopicListItem;
  groups: AdminGroupOverview[];
  participant_count: number;
  message_count: number;
  summary_count: number;
};

export type AdminDashboard = {
  topics: AdminTopicOverview[];
  active_topic_id: string | null;
  generated_at: string;
};

export type AdminThreadMessage = {
  message_id: number;
  thread_id: number;
  group_id: string;
  telegram_user_id: number | null;
  username: string | null;
  first_name: string | null;
  text: string;
  sent_at: string;
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

export async function fetchTopics(): Promise<TopicListItem[]> {
  const response = await fetch(`${getApiBaseUrl()}/topics`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load topics.");
  }
  return (await response.json()) as TopicListItem[];
}

export async function fetchTopic(topicId: string): Promise<TopicListItem> {
  const response = await fetch(`${getApiBaseUrl()}/topics/${topicId}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Failed to load topic.");
  }
  return (await response.json()) as TopicListItem;
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

async function adminFetch<T>(
  apiBaseUrl: string,
  adminKey: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
      ...init.headers,
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Admin request failed with ${response.status}.`);
  }
  return (await response.json()) as T;
}

export async function fetchAdminDashboard(
  apiBaseUrl: string,
  adminKey: string,
): Promise<AdminDashboard> {
  return adminFetch<AdminDashboard>(apiBaseUrl, adminKey, "/admin/dashboard");
}

export function toTimezoneAwareIso(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

export async function createAdminTopic(
  apiBaseUrl: string,
  adminKey: string,
  payload: {
    title: string;
    description?: string | null;
    closes_at?: string | null;
    cross_pollination_interval_seconds?: number;
    group_capacity?: number;
    seed_bullets?: string[];
  },
): Promise<void> {
  await adminFetch(apiBaseUrl, adminKey, "/admin/topics", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAdminTopic(
  apiBaseUrl: string,
  adminKey: string,
  topicId: string,
  payload: {
    title?: string;
    description?: string | null;
    closes_at?: string | null;
    cross_pollination_interval_seconds?: number;
    group_capacity?: number;
    seed_bullets?: string[];
  },
): Promise<void> {
  await adminFetch(apiBaseUrl, adminKey, `/admin/topics/${topicId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function summarizeAdminTopic(
  apiBaseUrl: string,
  adminKey: string,
  topicId: string,
): Promise<void> {
  await adminFetch(apiBaseUrl, adminKey, `/admin/summarize/${topicId}`, {
    method: "POST",
  });
}

export async function summarizeDueAdminTopics(
  apiBaseUrl: string,
  adminKey: string,
): Promise<void> {
  await adminFetch(apiBaseUrl, adminKey, "/admin/summarize-due", {
    method: "POST",
  });
}

export async function fetchAdminGroupMessages(
  apiBaseUrl: string,
  adminKey: string,
  groupId: string,
): Promise<AdminThreadMessage[]> {
  return adminFetch<AdminThreadMessage[]>(
    apiBaseUrl,
    adminKey,
    `/admin/groups/${groupId}/messages`,
  );
}
