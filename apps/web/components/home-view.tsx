import { TopicListItem } from "@/lib/api";

type HomeViewProps = {
  topics: TopicListItem[];
  botUsername: string;
};

function formatCloseDate(value: string | null): string {
  if (!value) {
    return "No closing date set";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getStatusLabel(topic: TopicListItem): string {
  return topic.status === "active" ? "Open now" : "Results available";
}

export function HomeView({ topics, botUsername }: HomeViewProps) {
  const activeTopic = topics.find((topic) => topic.status === "active") ?? null;
  const pastTopics = topics.filter((topic) => topic.status === "closed");
  const featuredTopic = activeTopic ?? pastTopics[0] ?? topics[0] ?? null;

  return (
    <main className="shell home-shell">
      <section className="hero">
        <p className="eyebrow">CORDA Deliberation</p>
        <h1>{featuredTopic?.title ?? "Next topic lands soon"}</h1>
        <p className="lede">
          {activeTopic
            ? (activeTopic.description ??
              "A structured public deliberation where each participant is routed into a small Telegram discussion group.")
            : "There is no live deliberation right now. The next topic will land soon; meanwhile, explore the summaries from previous discussions."}
        </p>
        <div className="meta-line">
          <span>{activeTopic ? `Closing: ${formatCloseDate(activeTopic.closes_at)}` : "No active topic"}</span>
          <span>{pastTopics.length} past {pastTopics.length === 1 ? "discussion" : "discussions"}</span>
        </div>
        <div className="actions">
          {activeTopic ? (
            <a
              className="primary-link"
              href={`https://t.me/${botUsername}?start=${activeTopic.id}`}
              target="_blank"
              rel="noreferrer"
            >
              Join a Group
            </a>
          ) : null}
          {featuredTopic ? (
            <a className="secondary-link" href={`/results?topicId=${featuredTopic.id}`}>
              {activeTopic ? "See Results" : "Read Latest Summary"}
            </a>
          ) : null}
        </div>
      </section>
      {topics.length > 0 ? (
        <section className="topic-rail-section" aria-labelledby="topic-rail-title">
          <div className="section-heading">
            <p className="eyebrow">Discussion archive</p>
            <h2 id="topic-rail-title">Past and current topics</h2>
          </div>
          <div className="topic-rail" aria-label="Topic carousel">
            {topics.map((topic, index) => (
              <a
                className={`topic-slide ${index === 0 ? "topic-slide-featured" : ""}`}
                href={`/results?topicId=${topic.id}`}
                key={topic.id}
              >
                <span className="topic-status">{getStatusLabel(topic)}</span>
                <h3>{topic.title}</h3>
                <p>
                  {topic.description ??
                    "A structured public deliberation summarized after closure."}
                </p>
                <span className="topic-date">
                  {topic.status === "active"
                    ? `Closes ${formatCloseDate(topic.closes_at)}`
                    : `Closed ${formatCloseDate(topic.closes_at)}`}
                </span>
              </a>
            ))}
          </div>
        </section>
      ) : (
        <section className="empty-state">
          <h2>No discussions published yet</h2>
          <p>The first topic will appear here once it is created.</p>
        </section>
      )}
    </main>
  );
}
