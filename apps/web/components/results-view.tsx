import { GroupSummary } from "@/lib/api";

type ResultsViewProps = {
  topicId: string;
  summaries: GroupSummary[];
};

export function ResultsView({ topicId, summaries }: ResultsViewProps) {
  return (
    <main className="shell results-shell">
      <section className="results-header">
        <p className="eyebrow">Topic results</p>
        <h1>Deliberation summaries</h1>
        <p className="lede">Topic ID: {topicId}</p>
      </section>
      {summaries.length === 0 ? (
        <section className="empty-state">
          <h2>No summaries yet</h2>
          <p>
            This topic has not been summarized yet. Results will appear after the discussion closes
            and the summarization job runs.
          </p>
        </section>
      ) : (
        <section className="summary-list">
          {summaries.map((summary, index) => (
            <article className="summary-entry" key={summary.group_id}>
              <p className="summary-kicker">Group {index + 1}</p>
              <pre>{summary.content}</pre>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
