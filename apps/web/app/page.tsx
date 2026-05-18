import { ErrorState } from "@/components/error-state";
import { HomeView } from "@/components/home-view";
import { fetchTopics } from "@/lib/api";

export default async function HomePage() {
  try {
    const topics = await fetchTopics();
    return renderHome(topics);
  } catch (error) {
    return (
      <ErrorState
        title="Topics unavailable"
        detail={error instanceof Error ? error.message : "Failed to load topics."}
      />
    );
  }
}

function renderHome(topics: Awaited<ReturnType<typeof fetchTopics>>) {
  return <HomeView topics={topics} />;
}
