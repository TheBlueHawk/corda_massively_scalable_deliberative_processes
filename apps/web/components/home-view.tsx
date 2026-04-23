import { ActiveTopic } from "@/lib/api";

type HomeViewProps = {
  topic: ActiveTopic;
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

export function HomeView({ topic, botUsername }: HomeViewProps) {
  return (
    <main className="shell poster">
      <section className="hero">
        <p className="eyebrow">CORDA Deliberation</p>
        <h1>{topic.title}</h1>
        <p className="lede">
          {topic.description ??
            "A structured public deliberation where each participant is routed into a small Telegram discussion group."}
        </p>
        <div className="meta-line">
          <span>Closing: {formatCloseDate(topic.closes_at)}</span>
          <span>One active topic at a time</span>
        </div>
        <div className="actions">
          <a
            className="primary-link"
            href={`https://t.me/${botUsername}?start=${topic.id}`}
            target="_blank"
            rel="noreferrer"
          >
            Join a Group
          </a>
          <a className="secondary-link" href={`/results?topicId=${topic.id}`}>
            See Results
          </a>
        </div>
      </section>
      <section className="support-grid">
        <div>
          <h2>Deliberate in parallel</h2>
          <p>
            Participants are assigned to the least-full discussion thread so each group stays small
            enough for genuine exchange.
          </p>
        </div>
        <div>
          <h2>Neutral synthesis</h2>
          <p>
            Once the topic closes, captured transcripts are summarized into concise points of
            agreement and disagreement.
          </p>
        </div>
      </section>
    </main>
  );
}
