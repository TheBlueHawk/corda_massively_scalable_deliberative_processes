import { ErrorState } from "@/components/error-state";
import { ResultsView } from "@/components/results-view";
import { fetchSummaries } from "@/lib/api";

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
    const summaries = await fetchSummaries(topicId);
    return renderResultsView(topicId, summaries);
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
  topicId: string,
  summaries: Awaited<ReturnType<typeof fetchSummaries>>,
) {
  return <ResultsView topicId={topicId} summaries={summaries} />;
}
