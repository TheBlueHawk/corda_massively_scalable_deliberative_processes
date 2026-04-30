import { ErrorState } from "@/components/error-state";
import { ResultsView } from "@/components/results-view";
import { fetchSummaries, fetchTopic } from "@/lib/api";

type ResultsPageProps = {
  searchParams: Promise<{ topicId?: string }>;
};

export default async function ResultsPage({ searchParams }: ResultsPageProps) {
  const params = await searchParams;
  const topicId = params.topicId;
  if (!topicId) {
    return (
      <ErrorState
        title="Topic missing"
        detail="Open the results page with a topicId query parameter."
      />
    );
  }
  try {
    const [topic, summaries] = await Promise.all([fetchTopic(topicId), fetchSummaries(topicId)]);
    return renderResultsView(topic, summaries);
  } catch (error) {
    return (
      <ErrorState
        title="Results unavailable"
        detail={error instanceof Error ? error.message : "Failed to load summaries."}
      />
    );
  }
}

function renderResultsView(
  topic: Awaited<ReturnType<typeof fetchTopic>>,
  summaries: Awaited<ReturnType<typeof fetchSummaries>>,
) {
  return <ResultsView topic={topic} summaries={summaries} />;
}
