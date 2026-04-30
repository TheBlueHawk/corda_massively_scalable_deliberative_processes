"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  AdminDashboard,
  AdminGroupOverview,
  AdminThreadMessage,
  AdminTopicOverview,
  closeAdminTopic,
  createAdminTopic,
  fetchAdminDashboard,
  fetchAdminGroupMessages,
  summarizeAdminTopic,
  summarizeDueAdminTopics,
  updateAdminTopic,
} from "@/lib/api";

type AdminDashboardViewProps = {
  apiBaseUrl: string;
};

type TopicFormState = {
  title: string;
  description: string;
  closesAt: string;
};

const emptyTopicForm: TopicFormState = {
  title: "",
  description: "",
  closesAt: "",
};

function getStoredAdminKey(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  if (typeof window.localStorage.getItem !== "function") {
    return null;
  }
  return window.localStorage.getItem("corda_admin_key");
}

function storeAdminKey(adminKey: string) {
  if (typeof window === "undefined") {
    return;
  }
  if (typeof window.localStorage.setItem !== "function") {
    return;
  }
  window.localStorage.setItem("corda_admin_key", adminKey);
}

function toLocalInputValue(value: string | null): string {
  if (!value) {
    return "";
  }
  return new Date(value).toISOString().slice(0, 16);
}

function toApiDate(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not set";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminDashboardView({ apiBaseUrl }: AdminDashboardViewProps) {
  const [adminKey, setAdminKey] = useState(() => getStoredAdminKey() ?? "");
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [topicForm, setTopicForm] = useState<TopicFormState>(emptyTopicForm);
  const [editForms, setEditForms] = useState<Record<string, TopicFormState>>({});
  const [selectedGroup, setSelectedGroup] = useState<AdminGroupOverview | null>(null);
  const [messages, setMessages] = useState<AdminThreadMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh(key = adminKey) {
    if (!key) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const nextDashboard = await fetchAdminDashboard(apiBaseUrl, key);
      setDashboard(nextDashboard);
      setEditForms(
        Object.fromEntries(
          nextDashboard.topics.map((item) => [
            item.topic.id,
            {
              title: item.topic.title,
              description: item.topic.description ?? "",
              closesAt: toLocalInputValue(item.topic.closes_at),
            },
          ]),
        ),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load admin dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const savedKey = getStoredAdminKey();
    if (savedKey) {
      const key = savedKey;
      async function loadSavedDashboard() {
        setLoading(true);
        setError(null);
        try {
          const nextDashboard = await fetchAdminDashboard(apiBaseUrl, key);
          setDashboard(nextDashboard);
          setEditForms(
            Object.fromEntries(
              nextDashboard.topics.map((item) => [
                item.topic.id,
                {
                  title: item.topic.title,
                  description: item.topic.description ?? "",
                  closesAt: toLocalInputValue(item.topic.closes_at),
                },
              ]),
            ),
          );
        } catch (caught) {
          setError(caught instanceof Error ? caught.message : "Failed to load admin dashboard.");
        } finally {
          setLoading(false);
        }
      }
      void loadSavedDashboard();
    }
  }, [apiBaseUrl]);

  async function runAction(action: () => Promise<void>, success: string) {
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      await refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Admin action failed.");
    } finally {
      setLoading(false);
    }
  }

  function saveKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    storeAdminKey(adminKey);
    void refresh(adminKey);
  }

  function createTopic(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runAction(
      () =>
        createAdminTopic(apiBaseUrl, adminKey, {
          title: topicForm.title,
          description: topicForm.description || null,
          closes_at: toApiDate(topicForm.closesAt),
        }),
      "Topic created.",
    );
    setTopicForm(emptyTopicForm);
  }

  function updateTopic(topicId: string) {
    const form = editForms[topicId];
    if (!form) {
      return;
    }
    void runAction(
      () =>
        updateAdminTopic(apiBaseUrl, adminKey, topicId, {
          title: form.title,
          description: form.description || null,
          closes_at: toApiDate(form.closesAt),
        }),
      "Topic updated.",
    );
  }

  async function loadMessages(group: AdminGroupOverview) {
    setSelectedGroup(group);
    setLoading(true);
    setError(null);
    try {
      setMessages(await fetchAdminGroupMessages(apiBaseUrl, adminKey, group.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load transcript.");
    } finally {
      setLoading(false);
    }
  }

  const totals = dashboard?.topics.reduce(
    (accumulator, item) => ({
      topics: accumulator.topics + 1,
      groups: accumulator.groups + item.groups.length,
      participants: accumulator.participants + item.participant_count,
      messages: accumulator.messages + item.message_count,
      summaries: accumulator.summaries + item.summary_count,
    }),
    { topics: 0, groups: 0, participants: 0, messages: 0, summaries: 0 },
  );

  return (
    <main className="shell admin-shell">
      <section className="admin-hero">
        <p className="eyebrow">Admin dashboard</p>
        <h1>Operate CORDA</h1>
        <p className="lede">
          Manage topics, trigger summaries, inspect Telegram groups, and verify captured
          transcripts from one protected surface.
        </p>
      </section>

      <form className="admin-keybar" onSubmit={saveKey}>
        <label>
          Admin key
          <input
            autoComplete="off"
            onChange={(event) => setAdminKey(event.target.value)}
            placeholder="Paste X_ADMIN_KEY"
            type="password"
            value={adminKey}
          />
        </label>
        <button type="submit">Load dashboard</button>
      </form>

      {error ? <p className="admin-error">{error}</p> : null}
      {notice ? <p className="admin-notice">{notice}</p> : null}
      {loading ? <p className="admin-muted">Working...</p> : null}

      {dashboard && totals ? (
        <>
          <section className="admin-metrics" aria-label="Platform metrics">
            <Metric label="Topics" value={totals.topics} />
            <Metric label="Groups" value={totals.groups} />
            <Metric label="Participants" value={totals.participants} />
            <Metric label="Messages" value={totals.messages} />
            <Metric label="Summaries" value={totals.summaries} />
          </section>

          <section className="admin-panel">
            <div>
              <p className="eyebrow">Topic management</p>
              <h2>Create a topic</h2>
            </div>
            <form className="admin-form" onSubmit={createTopic}>
              <input
                onChange={(event) =>
                  setTopicForm((current) => ({ ...current, title: event.target.value }))
                }
                placeholder="Topic title"
                required
                value={topicForm.title}
              />
              <textarea
                onChange={(event) =>
                  setTopicForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                placeholder="Description"
                value={topicForm.description}
              />
              <input
                onChange={(event) =>
                  setTopicForm((current) => ({ ...current, closesAt: event.target.value }))
                }
                type="datetime-local"
                value={topicForm.closesAt}
              />
              <button type="submit">Create topic</button>
            </form>
            <button
              className="admin-secondary-button"
              onClick={() =>
                void runAction(
                  () => summarizeDueAdminTopics(apiBaseUrl, adminKey),
                  "Due topics summarized.",
                )
              }
              type="button"
            >
              Summarize due topics
            </button>
          </section>

          <section className="admin-topic-list">
            {dashboard.topics.map((item) => (
              <TopicAdminCard
                editForm={editForms[item.topic.id] ?? emptyTopicForm}
                item={item}
                key={item.topic.id}
                onClose={() =>
                  void runAction(
                    () => closeAdminTopic(apiBaseUrl, adminKey, item.topic.id),
                    "Topic closed.",
                  )
                }
                onEditChange={(form) =>
                  setEditForms((current) => ({ ...current, [item.topic.id]: form }))
                }
                onLoadMessages={loadMessages}
                onSummarize={() =>
                  void runAction(
                    () => summarizeAdminTopic(apiBaseUrl, adminKey, item.topic.id),
                    "Topic summarized.",
                  )
                }
                onUpdate={() => updateTopic(item.topic.id)}
              />
            ))}
          </section>

          <TranscriptPanel group={selectedGroup} messages={messages} />
        </>
      ) : null}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="admin-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TopicAdminCard({
  editForm,
  item,
  onClose,
  onEditChange,
  onLoadMessages,
  onSummarize,
  onUpdate,
}: {
  editForm: TopicFormState;
  item: AdminTopicOverview;
  onClose: () => void;
  onEditChange: (form: TopicFormState) => void;
  onLoadMessages: (group: AdminGroupOverview) => void;
  onSummarize: () => void;
  onUpdate: () => void;
}) {
  return (
    <article className="admin-topic-card">
      <div className="admin-topic-header">
        <div>
          <p className="eyebrow">{item.topic.status}</p>
          <h2>{item.topic.title}</h2>
          <p>{item.topic.description ?? "No description set."}</p>
          <p className="admin-muted">Closes: {formatDate(item.topic.closes_at)}</p>
        </div>
        <div className="admin-actions">
          <button onClick={onSummarize} type="button">
            Summarize
          </button>
          {item.topic.status === "active" ? (
            <button onClick={onClose} type="button">
              Close
            </button>
          ) : null}
        </div>
      </div>

      <form className="admin-form admin-edit-form" onSubmit={(event) => event.preventDefault()}>
        <input
          onChange={(event) => onEditChange({ ...editForm, title: event.target.value })}
          value={editForm.title}
        />
        <textarea
          onChange={(event) =>
            onEditChange({
              ...editForm,
              description: event.target.value,
            })
          }
          value={editForm.description}
        />
        <input
          onChange={(event) => onEditChange({ ...editForm, closesAt: event.target.value })}
          type="datetime-local"
          value={editForm.closesAt}
        />
        <button onClick={onUpdate} type="button">
          Save edits
        </button>
      </form>

      <div className="admin-group-table">
        {item.groups.length === 0 ? (
          <p className="admin-muted">No groups assigned yet.</p>
        ) : (
          item.groups.map((group) => (
            <button key={group.id} onClick={() => onLoadMessages(group)} type="button">
              <span>{group.telegram_topic_name}</span>
              <span>
                {group.member_count}/{group.capacity} members
              </span>
              <span>{group.message_count} messages</span>
              <span>{group.has_summary ? "Summarized" : "No summary"}</span>
            </button>
          ))
        )}
      </div>
    </article>
  );
}

function TranscriptPanel({
  group,
  messages,
}: {
  group: AdminGroupOverview | null;
  messages: AdminThreadMessage[];
}) {
  if (!group) {
    return null;
  }
  return (
    <section className="admin-panel">
      <p className="eyebrow">Transcript</p>
      <h2>{group.telegram_topic_name}</h2>
      {messages.length === 0 ? (
        <p className="admin-muted">No captured messages for this group.</p>
      ) : (
        <div className="admin-transcript">
          {messages.map((message) => (
            <article key={`${message.thread_id}-${message.message_id}`}>
              <span>{formatDate(message.sent_at)}</span>
              <strong>
                {message.first_name ?? message.username ?? message.telegram_user_id ?? "Unknown"}
              </strong>
              <p>{message.text}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
