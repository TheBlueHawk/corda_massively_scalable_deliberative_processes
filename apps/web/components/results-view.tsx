import { GroupSummary, TopicListItem } from "@/lib/api";

import { MarkdownSummary } from "./markdown-summary";

type ResultsViewProps = {
  topic: TopicListItem;
  summaries: GroupSummary[];
};

export function ResultsView({ topic, summaries }: ResultsViewProps) {
  return (
    <main className="shell results-shell">
      <section className="results-header">
        <p className="eyebrow">Summary</p>
        <h1>{topic.title}</h1>
        {topic.description ? <p className="lede">{topic.description}</p> : null}
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
              <MarkdownSummary content={summary.content} />
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
