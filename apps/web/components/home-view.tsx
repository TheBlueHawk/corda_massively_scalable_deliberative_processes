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

function getJoinUrl(botUsername: string, topicId: string): string {
  return `https://t.me/${botUsername}?start=${topicId}`;
}

export function HomeView({ topics, botUsername }: HomeViewProps) {
  const activeTopic = topics.find((topic) => topic.status === "active") ?? null;
  const pastTopics = topics.filter((topic) => topic.status === "closed");
  const latestClosedTopic = pastTopics[0] ?? null;

  return (
    <main className="shell home-shell">
      <section className="hero">
        <p className="eyebrow">{activeTopic ? "Live deliberation" : "Between topics"}</p>
        <h1>{activeTopic?.title ?? "Next topic lands soon"}</h1>
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
              href={getJoinUrl(botUsername, activeTopic.id)}
              target="_blank"
              rel="noreferrer"
            >
              Join a Group
            </a>
          ) : null}
          {latestClosedTopic ? (
            <a className="secondary-link" href={`/results?topicId=${latestClosedTopic.id}`}>
              {activeTopic ? "See Past Results" : "Read Latest Summary"}
            </a>
          ) : null}
        </div>
      </section>
      <section className="intro-section" aria-labelledby="intro-title">
        <div>
          <p className="eyebrow">Why CORDA</p>
          <h2 id="intro-title">Have something to say? Then become part of our conversations.</h2>
        </div>
        <div className="intro-copy">
          <p>
            We believe every voice matters. Not because all opinions are the same, but because every
            perspective adds something we cannot see alone.
          </p>
          <p>
            We turn fast-moving chats into structured dialogue - focused on understanding, not
            winning. A space to reflect, challenge ideas, and think through societal issues together.
          </p>
          <p>
            No silencing. Instead, we guide conversations through thoughtful prompts that encourage
            clarity, openness, and reflection.
          </p>
          <p>
            Our goal: better dialogue, shared responsibility, and more meaningful outcomes. Join us
            on Telegram and take part in your first structured discussion.
          </p>
          {activeTopic ? (
            <a
              className="text-link"
              href={getJoinUrl(botUsername, activeTopic.id)}
              target="_blank"
              rel="noreferrer"
            >
              Join us on Telegram
            </a>
          ) : (
            <p className="soft-note">The next discussion will appear here soon.</p>
          )}
        </div>
      </section>
      {pastTopics.length > 0 ? (
        <section className="topic-rail-section" aria-labelledby="topic-rail-title">
          <div className="section-heading">
            <h2 className="eyebrow" id="topic-rail-title">
              Discussion archive
            </h2>
          </div>
          <div className="topic-rail" aria-label="Topic carousel">
            {pastTopics.map((topic, index) => (
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
                <span className="topic-date">Closed {formatCloseDate(topic.closes_at)}</span>
              </a>
            ))}
          </div>
        </section>
      ) : topics.length === 0 ? (
        <section className="empty-state">
          <h2>No discussions published yet</h2>
          <p>The first topic will appear here once it is created.</p>
        </section>
      ) : null}
    </main>
  );
}
