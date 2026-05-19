import { ChatView } from "@/components/chat-view";
import { fetchTopics } from "@/lib/api";
import type { ActiveTopic } from "@/lib/api";

export default async function AppPage() {
  let activeTopic: ActiveTopic | null = null;
  try {
    const topics = await fetchTopics();
    activeTopic = topics.find((t) => t.status === "active") ?? null;
  } catch {
    // Render without topic; ChatView shows an appropriate message.
  }
  return <ChatView activeTopic={activeTopic} />;
}
