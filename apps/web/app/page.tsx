import { ErrorState } from "@/components/error-state";
import { HomeView } from "@/components/home-view";
import { fetchActiveTopic } from "@/lib/api";

export default async function HomePage() {
  try {
    const topic = await fetchActiveTopic();
    const botUsername = process.env.TELEGRAM_BOT_USERNAME;
    if (!botUsername) {
      throw new Error("Missing TELEGRAM_BOT_USERNAME environment variable.");
    }
    return renderHomeView(topic, botUsername);
  } catch (error) {
    return (
      <ErrorState
        title="Topic unavailable"
        detail={error instanceof Error ? error.message : "Failed to load the active topic."}
      />
    );
  }
}

function renderHomeView(
  topic: Awaited<ReturnType<typeof fetchActiveTopic>>,
  botUsername: string,
) {
  return <HomeView topic={topic} botUsername={botUsername} />;
}
