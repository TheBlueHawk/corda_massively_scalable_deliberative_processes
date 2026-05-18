"use client";

import { useEffect, useRef, useState } from "react";
import type { ActiveTopic, ChatGroup, ChatMessage } from "@/lib/api";
import {
  createParticipant,
  getChatStreamUrl,
  getGroupMessages,
  getMyGroup,
  joinTopic,
  sendChatMessage,
} from "@/lib/api";

const PARTICIPANT_ID_KEY = "corda_participant_id";
const DISPLAY_NAME_KEY = "corda_display_name";

type Phase =
  | { kind: "loading" }
  | { kind: "identity" }
  | { kind: "no-topic" }
  | { kind: "ready"; topicId: string }
  | { kind: "chat"; group: ChatGroup; messages: ChatMessage[] };

function formatTime(iso: string): string {
  return new Intl.DateTimeFormat("en", { timeStyle: "short" }).format(new Date(iso));
}

type ChatViewProps = {
  activeTopic: ActiveTopic | null;
};

export function ChatView({ activeTopic }: ChatViewProps) {
  // Always start with "loading" — server and client must agree on first render.
  // All localStorage access happens in the effect below after hydration.
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });
  const [nameInput, setNameInput] = useState("");
  const [messageInput, setMessageInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);
  const participantIdRef = useRef<string | null>(null);

  useEffect(() => {
    void (async () => {
      const storedId = localStorage.getItem(PARTICIPANT_ID_KEY);
      participantIdRef.current = storedId;

      if (!storedId) {
        setPhase({ kind: "identity" });
        return;
      }
      if (!activeTopic) {
        setPhase({ kind: "no-topic" });
        return;
      }
      try {
        const group = await getMyGroup(activeTopic.id, storedId);
        if (group) {
          const messages = await getGroupMessages(group.id, storedId);
          enterChat(storedId, group, messages);
        } else {
          setPhase({ kind: "ready", topicId: activeTopic.id });
        }
      } catch {
        setPhase({ kind: "ready", topicId: activeTopic.id });
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function enterChat(participantId: string, group: ChatGroup, initialMessages?: ChatMessage[]) {
    setPhase({ kind: "chat", group, messages: initialMessages ?? [] });
    esRef.current?.close();
    const es = new EventSource(`${getChatStreamUrl(group.id)}?participant_id=${participantId}`);
    esRef.current = es;
    es.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as ChatMessage;
        setPhase((prev) => {
          if (prev.kind !== "chat") return prev;
          if (prev.messages.some((m) => m.id === msg.id)) return prev;
          return { ...prev, messages: [...prev.messages, msg] };
        });
      } catch {
        // ignore malformed SSE events
      }
    };
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [phase]);

  useEffect(() => () => esRef.current?.close(), []);

  async function handleSetName(e: React.FormEvent) {
    e.preventDefault();
    const name = nameInput.trim();
    if (!name) return;
    setError(null);
    try {
      const participant = await createParticipant(name);
      localStorage.setItem(PARTICIPANT_ID_KEY, participant.id);
      localStorage.setItem(DISPLAY_NAME_KEY, participant.display_name);
      participantIdRef.current = participant.id;
      setPhase(activeTopic ? { kind: "ready", topicId: activeTopic.id } : { kind: "no-topic" });
    } catch {
      setError("Could not save your name. Please try again.");
    }
  }

  async function handleJoin() {
    const pid = participantIdRef.current;
    if (!pid || phase.kind !== "ready") return;
    setError(null);
    try {
      const result = await joinTopic(phase.topicId, pid);
      enterChat(pid, result.group, result.messages);
    } catch {
      setError("Could not join the discussion. Please try again.");
    }
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = messageInput.trim();
    const pid = participantIdRef.current;
    if (!text || !pid || phase.kind !== "chat" || sending) return;
    setSending(true);
    setError(null);
    try {
      await sendChatMessage(phase.group.id, pid, text);
      setMessageInput("");
    } catch {
      setError("Failed to send. Please try again.");
    } finally {
      setSending(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend(e as unknown as React.FormEvent);
    }
  }

  if (phase.kind === "loading") {
    return (
      <main className="shell chat-shell">
        <div className="chat-stage" />
      </main>
    );
  }

  if (phase.kind === "identity") {
    return (
      <main className="shell chat-shell">
        <div className="chat-stage chat-stage--centered">
          <div className="chat-card">
            <p className="eyebrow">Welcome</p>
            <h1 className="chat-card-heading">What should we call you?</h1>
            <p className="chat-card-sub">
              You can use any name — real or anonymous. It will only be visible to participants in
              your group.
            </p>
            <form onSubmit={handleSetName} className="chat-name-form">
              <div className="chat-name-field">
                <input
                  type="text"
                  className="chat-name-input"
                  placeholder="Your display name"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  maxLength={80}
                  required
                  autoFocus
                />
                <div className="chat-name-underline" />
              </div>
              <button type="submit" className="primary-link chat-name-submit">
                Continue →
              </button>
            </form>
            {error && <p className="chat-error">{error}</p>}
          </div>
        </div>
      </main>
    );
  }

  if (phase.kind === "no-topic") {
    return (
      <main className="shell chat-shell">
        <div className="chat-stage chat-stage--centered">
          <div className="chat-card">
            <p className="eyebrow">Between discussions</p>
            <h1 className="chat-card-heading">No active deliberation right now.</h1>
            <p className="chat-card-sub">
              The next topic will appear here soon. Check back later or browse past summaries.
            </p>
            <a className="primary-link" href="/results">
              Browse past summaries
            </a>
          </div>
        </div>
      </main>
    );
  }

  if (phase.kind === "ready") {
    return (
      <main className="shell chat-shell">
        <div className="chat-stage chat-stage--centered">
          <div className="chat-card">
            <p className="eyebrow">Live deliberation</p>
            <h1 className="chat-card-heading">{activeTopic?.title ?? "Active discussion"}</h1>
            {activeTopic?.description && (
              <p className="chat-card-sub">{activeTopic.description}</p>
            )}
            <div className="actions">
              <button className="primary-link" onClick={handleJoin}>
                Join the deliberation
              </button>
            </div>
            {error && <p className="chat-error">{error}</p>}
          </div>
        </div>
      </main>
    );
  }

  // phase.kind === "chat"
  const { group, messages } = phase;
  return (
    <main className="shell chat-shell">
      <div className="chat-stage chat-stage--thread">
        <header className="chat-header">
          <div>
            <p className="eyebrow">Live group</p>
            <h2 className="chat-header-title">{group.telegram_topic_name}</h2>
          </div>
          <span className="chat-header-meta">
            {group.member_count} / {group.capacity} participants
          </span>
        </header>

        <div className="chat-messages" role="log" aria-live="polite">
          {messages.length === 0 && (
            <p className="chat-empty">No messages yet. Start the conversation.</p>
          )}
          {messages.map((msg) => (
            <article
              key={msg.id}
              className={`chat-msg ${msg.is_moderator ? "chat-msg--mod" : ""}`}
            >
              <span className="chat-msg-sender">
                {msg.is_moderator ? "Moderator" : msg.display_name}
              </span>
              <p className="chat-msg-text">{msg.text}</p>
              <time className="chat-msg-time">{formatTime(msg.sent_at)}</time>
            </article>
          ))}
          <div ref={bottomRef} />
        </div>

        <form className="chat-input-bar" onSubmit={handleSend}>
          <textarea
            className="chat-input"
            placeholder="Share your perspective… (Enter to send, Shift+Enter for newline)"
            value={messageInput}
            onChange={(e) => setMessageInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            maxLength={4000}
            disabled={sending}
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={sending || !messageInput.trim()}
          >
            Send
          </button>
        </form>
        {error && <p className="chat-error">{error}</p>}
      </div>
    </main>
  );
}
