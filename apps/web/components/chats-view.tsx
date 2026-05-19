"use client";

import { useEffect, useRef, useState } from "react";
import type { ChatMessage, ParticipantGroupEntry } from "@/lib/api";
import {
  getChatStreamUrl,
  getGroupMessages,
  getMyGroups,
  sendChatMessage,
} from "@/lib/api";

const PARTICIPANT_ID_KEY = "corda_participant_id";

type SidebarPhase =
  | { kind: "loading" }
  | { kind: "no-identity" }
  | { kind: "empty" }
  | { kind: "ready"; entries: ParticipantGroupEntry[] };

type ThreadPhase =
  | { kind: "none" }
  | { kind: "loading" }
  | { kind: "ready"; entry: ParticipantGroupEntry; messages: ChatMessage[] };

function formatTime(iso: string): string {
  return new Intl.DateTimeFormat("en", { timeStyle: "short" }).format(new Date(iso));
}

export function ChatsView() {
  const [sidebar, setSidebar] = useState<SidebarPhase>({ kind: "loading" });
  const [thread, setThread] = useState<ThreadPhase>({ kind: "none" });
  const [messageInput, setMessageInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const participantIdRef = useRef<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const pid = localStorage.getItem(PARTICIPANT_ID_KEY);
    if (!pid) {
      setSidebar({ kind: "no-identity" });
      return;
    }
    participantIdRef.current = pid;
    getMyGroups(pid)
      .then((entries) => {
        if (entries.length === 0) {
          setSidebar({ kind: "empty" });
        } else {
          setSidebar({ kind: "ready", entries });
          selectGroup(entries[0], pid);
        }
      })
      .catch(() => setSidebar({ kind: "empty" }));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread]);

  useEffect(() => () => esRef.current?.close(), []);

  function selectGroup(entry: ParticipantGroupEntry, pid: string) {
    esRef.current?.close();
    setThread({ kind: "loading" });
    setError(null);
    setMessageInput("");
    getGroupMessages(entry.group.id, pid)
      .then((messages) => {
        setThread({ kind: "ready", entry, messages });
        const es = new EventSource(
          `${getChatStreamUrl(entry.group.id)}?participant_id=${pid}`,
        );
        esRef.current = es;
        es.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data as string) as ChatMessage;
            setThread((prev) => {
              if (prev.kind !== "ready" || prev.entry.group.id !== entry.group.id) return prev;
              if (prev.messages.some((m) => m.id === msg.id)) return prev;
              return { ...prev, messages: [...prev.messages, msg] };
            });
          } catch {
            // ignore malformed SSE
          }
        };
      })
      .catch(() => setThread({ kind: "none" }));
  }

  function handleSelectGroup(entry: ParticipantGroupEntry) {
    const pid = participantIdRef.current;
    if (!pid) return;
    if (thread.kind === "ready" && thread.entry.group.id === entry.group.id) return;
    selectGroup(entry, pid);
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const text = messageInput.trim();
    const pid = participantIdRef.current;
    if (!text || !pid || thread.kind !== "ready" || sending) return;
    setSending(true);
    setError(null);
    try {
      await sendChatMessage(thread.entry.group.id, pid, text);
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

  const selectedId = thread.kind === "ready" ? thread.entry.group.id : null;

  return (
    <div className="chats-shell">
      {/* ── Left sidebar ── */}
      <aside className="chats-sidebar">
        <div className="chats-sidebar-header">
          <p className="chats-sidebar-title">Your groups</p>
        </div>
        <div className="chats-group-list">
          {sidebar.kind === "loading" && (
            <p className="chats-sidebar-notice">Loading…</p>
          )}
          {sidebar.kind === "no-identity" && (
            <p className="chats-sidebar-notice">
              <a className="chats-sidebar-link" href="/app">
                Join a deliberation
              </a>{" "}
              to see your groups here.
            </p>
          )}
          {sidebar.kind === "empty" && (
            <p className="chats-sidebar-notice">
              You have not joined any group yet.{" "}
              <a className="chats-sidebar-link" href="/app">
                Join one →
              </a>
            </p>
          )}
          {sidebar.kind === "ready" &&
            sidebar.entries.map((entry) => (
              <button
                key={entry.group.id}
                className={`chats-group-btn chats-group-item${selectedId === entry.group.id ? " chats-group-item--active" : ""}`}
                onClick={() => handleSelectGroup(entry)}
              >
                <p className={`chats-group-topic${entry.topic.status === "closed" ? " chats-group-closed" : ""}`}>
                  {entry.topic.title}
                </p>
                <p className="chats-group-name">{entry.group.telegram_topic_name}</p>
                <div className="chats-group-meta">
                  <span>
                    {entry.group.member_count} / {entry.group.capacity}
                  </span>
                  {entry.topic.status === "closed" && <span>· ended</span>}
                </div>
              </button>
            ))}
        </div>
      </aside>

      {/* ── Right thread pane ── */}
      {thread.kind === "none" && (
        <div className="chat-stage chat-stage--centered">
          <p className="chats-empty-pane">Select a group to start reading.</p>
        </div>
      )}
      {thread.kind === "loading" && (
        <div className="chat-stage chat-stage--centered">
          <p className="chats-empty-pane">Loading…</p>
        </div>
      )}
      {thread.kind === "ready" && (
        <div className="chat-stage chat-stage--thread">
          <header className="chat-header">
            <div>
              <p className="eyebrow">{thread.entry.topic.title}</p>
              <h2 className="chat-header-title">{thread.entry.group.telegram_topic_name}</h2>
            </div>
            <span className="chat-header-meta">
              {thread.entry.group.member_count} / {thread.entry.group.capacity} participants
            </span>
          </header>

          <div className="chat-messages" role="log" aria-live="polite">
            {thread.messages.length === 0 && (
              <p className="chat-empty">No messages yet.</p>
            )}
            {thread.messages.map((msg) => (
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

          {thread.entry.topic.status === "active" ? (
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
          ) : (
            <p className="chats-closed-notice">This deliberation has ended — read only</p>
          )}
          {error && <p className="chat-error">{error}</p>}
        </div>
      )}
    </div>
  );
}
