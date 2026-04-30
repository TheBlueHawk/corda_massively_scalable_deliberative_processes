import { ErrorState } from "@/components/error-state";
import { HomeView } from "@/components/home-view";
import { fetchTopics } from "@/lib/api";

export default async function HomePage() {
  try {
    const topics = await fetchTopics();
    const botUsername = process.env.TELEGRAM_BOT_USERNAME;
    if (!botUsername) {
      throw new Error("Missing TELEGRAM_BOT_USERNAME environment variable.");
    }
    return renderHomeView(topics, botUsername);
  } catch (error) {
    return (
      <ErrorState
        title="Topics unavailable"
        detail={error instanceof Error ? error.message : "Failed to load topics."}
      />
    );
  }
}

function renderHomeView(
  topics: Awaited<ReturnType<typeof fetchTopics>>,
  botUsername: string,
) {
  return <HomeView topics={topics} botUsername={botUsername} />;
}
