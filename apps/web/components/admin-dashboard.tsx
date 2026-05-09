"use client";

import { FormEvent, KeyboardEvent, useEffect, useState } from "react";

import {
  AdminDashboard,
  AdminGroupOverview,
  AdminThreadMessage,
  AdminTopicOverview,
  createAdminTopic,
  fetchAdminDashboard,
  fetchAdminGroupMessages,
  generateAdminTopicCover,
  toTimezoneAwareIso,
  updateAdminTopic,
} from "@/lib/api";

type AdminDashboardViewProps = {
  apiBaseUrl: string;
};

type TopicFormState = {
  title: string;
  description: string;
  closesAt: string;
  crossPollinationIntervalDays: string;
  groupCapacity: string;
  seedBullets: string;
};

type TopicEndFormState = {
  title: string;
  description: string;
  closesAt: string;
  crossPollinationIntervalDays: string;
  groupCapacity: string;
  seedBullets: string;
};

type PendingConfirmation =
  | {
      kind: "create-topic";
    }
  | {
      kind: "update-end-date";
      topicId: string;
    };

const DEFAULT_GROUP_CAPACITY = "8";

const emptyTopicForm: TopicFormState = {
  title: "",
  description: "",
  closesAt: "",
  crossPollinationIntervalDays: "1",
  groupCapacity: DEFAULT_GROUP_CAPACITY,
  seedBullets: "",
};

const emptyTopicEndForm: TopicEndFormState = {
  title: "",
  description: "",
  closesAt: "",
  crossPollinationIntervalDays: "1",
  groupCapacity: DEFAULT_GROUP_CAPACITY,
  seedBullets: "",
};

function parseSeedBullets(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.replace(/^[-•·\s]+/, "").trim())
    .filter((line) => line.length > 0);
}

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

function clearStoredAdminKey() {
  if (typeof window === "undefined") {
    return;
  }
  if (typeof window.localStorage.removeItem !== "function") {
    return;
  }
  window.localStorage.removeItem("corda_admin_key");
}

function toLocalInputValue(value: string | null): string {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60_000);
  return local.toISOString().slice(0, 16);
}

function getCurrentLocalInputValue(): string {
  return toLocalInputValue(new Date().toISOString());
}

function isPastLocalInputValue(value: string): boolean {
  return value.length > 0 && new Date(value).getTime() < Date.now();
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not set";
  }
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    timeZoneName: "short",
    year: "numeric",
  }).format(new Date(value));
}

function secondsToDaysInput(seconds: number): string {
  return String(seconds / 86_400);
}

function daysInputToSeconds(value: string): number {
  return Math.max(1, Math.round(Number(value) * 86_400));
}

function parseGroupCapacity(value: string): number {
  const parsed = Math.round(Number(value));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 8;
}

export function AdminDashboardView({ apiBaseUrl }: AdminDashboardViewProps) {
  const [adminKey, setAdminKey] = useState(() => getStoredAdminKey() ?? "");
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [topicForm, setTopicForm] = useState<TopicFormState>(emptyTopicForm);
  const [editForms, setEditForms] = useState<Record<string, TopicEndFormState>>({});
  const [isCreateTopicOpen, setIsCreateTopicOpen] = useState(false);
  const [editingEndTopicId, setEditingEndTopicId] = useState<string | null>(null);
  const [pendingConfirmation, setPendingConfirmation] = useState<PendingConfirmation | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<AdminGroupOverview | null>(null);
  const [messages, setMessages] = useState<AdminThreadMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isLoggedIn = dashboard !== null && adminKey.length > 0;

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
              crossPollinationIntervalDays: secondsToDaysInput(
                item.topic.cross_pollination_interval_seconds,
              ),
              groupCapacity: String(item.topic.group_capacity),
              seedBullets: (item.topic.seed_bullets ?? []).join("\n"),
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
                  crossPollinationIntervalDays: secondsToDaysInput(
                    item.topic.cross_pollination_interval_seconds,
                  ),
                  groupCapacity: String(item.topic.group_capacity),
                  seedBullets: (item.topic.seed_bullets ?? []).join("\n"),
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

  function signOut() {
    clearStoredAdminKey();
    setAdminKey("");
    setDashboard(null);
    setEditForms({});
    setSelectedGroup(null);
    setMessages([]);
    setNotice("Admin session cleared.");
    setError(null);
  }

  function executeCreateTopic() {
    if (isPastLocalInputValue(topicForm.closesAt)) {
      setError("Deliberation end cannot be in the past.");
      setTopicForm((current) => ({ ...current, closesAt: getCurrentLocalInputValue() }));
      return;
    }
    void runAction(
      () =>
        createAdminTopic(apiBaseUrl, adminKey, {
          title: topicForm.title,
          description: topicForm.description || null,
          closes_at: toTimezoneAwareIso(topicForm.closesAt),
          cross_pollination_interval_seconds: daysInputToSeconds(
            topicForm.crossPollinationIntervalDays,
          ),
          group_capacity: parseGroupCapacity(topicForm.groupCapacity),
          seed_bullets: parseSeedBullets(topicForm.seedBullets),
        }),
      "Topic created.",
    );
    setTopicForm(emptyTopicForm);
    setIsCreateTopicOpen(false);
  }

  function createTopic(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (activeTopics.length > 0) {
      setPendingConfirmation({ kind: "create-topic" });
      return;
    }
    executeCreateTopic();
  }

  function generateCover(topicId: string) {
    void runAction(
      () => generateAdminTopicCover(apiBaseUrl, adminKey, topicId),
      "Cover image generated.",
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
  const activeTopics = dashboard?.topics.filter((item) => item.topic.status === "active") ?? [];
  const pastTopics = dashboard?.topics.filter((item) => item.topic.status === "closed") ?? [];
  const minimumEndDate = getCurrentLocalInputValue();

  function executeUpdateTopic(topicId: string) {
    const form = editForms[topicId];
    if (!form) {
      return;
    }
    if (isPastLocalInputValue(form.closesAt)) {
      const currentMinimumEndDate = getCurrentLocalInputValue();
      setError("Deliberation end cannot be in the past.");
      setEditingEndTopicId(null);
      setEditForms((current) => ({
        ...current,
        [topicId]: { ...form, closesAt: currentMinimumEndDate },
      }));
      return;
    }
    const trimmedTitle = form.title.trim();
    if (!trimmedTitle) {
      setError("Topic title cannot be empty.");
      return;
    }
    const trimmedDescription = form.description.trim();
    void runAction(
      () =>
        updateAdminTopic(apiBaseUrl, adminKey, topicId, {
          title: trimmedTitle,
          description: trimmedDescription ? trimmedDescription : null,
          closes_at: toTimezoneAwareIso(form.closesAt),
          cross_pollination_interval_seconds: daysInputToSeconds(
            form.crossPollinationIntervalDays,
          ),
          group_capacity: parseGroupCapacity(form.groupCapacity),
          seed_bullets: parseSeedBullets(form.seedBullets),
        }),
      "Topic updated.",
    );
    setEditingEndTopicId(null);
  }

  function requestUpdateTopic(topicId: string) {
    const form = editForms[topicId];
    const topic = dashboard?.topics.find((item) => item.topic.id === topicId)?.topic;
    if (!form || !topic) {
      return;
    }
    if (
      form.title.trim() === topic.title &&
      form.description.trim() === (topic.description ?? "") &&
      form.closesAt === toLocalInputValue(topic.closes_at) &&
      daysInputToSeconds(form.crossPollinationIntervalDays) ===
        topic.cross_pollination_interval_seconds &&
      parseGroupCapacity(form.groupCapacity) === topic.group_capacity &&
      JSON.stringify(parseSeedBullets(form.seedBullets)) ===
        JSON.stringify(topic.seed_bullets ?? [])
    ) {
      setEditingEndTopicId(null);
      return;
    }
    if (isPastLocalInputValue(form.closesAt)) {
      const currentMinimumEndDate = getCurrentLocalInputValue();
      setError("Deliberation end cannot be in the past.");
      setEditingEndTopicId(null);
      setEditForms((current) => ({
        ...current,
        [topicId]: { ...form, closesAt: currentMinimumEndDate },
      }));
      return;
    }
    setPendingConfirmation({ kind: "update-end-date", topicId });
  }

  function cancelConfirmation() {
    if (pendingConfirmation?.kind === "update-end-date") {
      setEditForms((current) => {
        const topic = dashboard?.topics.find(
          (item) => item.topic.id === pendingConfirmation.topicId,
        )?.topic;
        if (!topic) {
          return current;
        }
        return {
          ...current,
          [pendingConfirmation.topicId]: {
            title: topic.title,
            description: topic.description ?? "",
            closesAt: toLocalInputValue(topic.closes_at),
            crossPollinationIntervalDays: secondsToDaysInput(
              topic.cross_pollination_interval_seconds,
            ),
            groupCapacity: String(topic.group_capacity),
            seedBullets: (topic.seed_bullets ?? []).join("\n"),
          },
        };
      });
      setEditingEndTopicId(null);
    }
    setPendingConfirmation(null);
  }

  function confirmPendingAction() {
    const confirmation = pendingConfirmation;
    setPendingConfirmation(null);
    if (!confirmation) {
      return;
    }
    if (confirmation.kind === "create-topic") {
      executeCreateTopic();
      return;
    }
    executeUpdateTopic(confirmation.topicId);
  }

  return (
    <main className="shell admin-shell">
      <header className="admin-topline">
        <p className="eyebrow">Admin dashboard</p>
        {isLoggedIn ? (
          <button className="admin-sign-out-button" onClick={signOut} type="button">
            Sign out
          </button>
        ) : null}
      </header>

      {isLoggedIn ? (
        <section className="admin-keybar" aria-label="Admin session">
          <button onClick={() => void refresh()} type="button">
            Refresh dashboard
          </button>
        </section>
      ) : (
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
      )}

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

          <section className="admin-topic-list">
            {activeTopics.map((item) => (
              <TopicAdminCard
                editForm={editForms[item.topic.id] ?? emptyTopicEndForm}
                isEditingEnd={editingEndTopicId === item.topic.id}
                item={item}
                key={item.topic.id}
                minimumEndDate={minimumEndDate}
                onEditChange={(form) =>
                  setEditForms((current) => ({ ...current, [item.topic.id]: form }))
                }
                onEditEndStart={() => setEditingEndTopicId(item.topic.id)}
                onGenerateCover={() => generateCover(item.topic.id)}
                onLoadMessages={loadMessages}
                onUpdate={() => requestUpdateTopic(item.topic.id)}
              />
            ))}
            <div className="admin-create-topic">
              <button
                className="admin-text-button"
                onClick={() => setIsCreateTopicOpen((current) => !current)}
                type="button"
              >
                + add topic
              </button>
              {isCreateTopicOpen ? (
                <form className="admin-form admin-create-form" onSubmit={createTopic}>
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
                    aria-label="Deliberation end in your timezone"
                    min={minimumEndDate}
                    type="datetime-local"
                    value={topicForm.closesAt}
                  />
                  <label>
                    Cross-pollination interval (days)
                    <input
                      min="0.01"
                      onChange={(event) =>
                        setTopicForm((current) => ({
                          ...current,
                          crossPollinationIntervalDays: event.target.value,
                        }))
                      }
                      step="0.01"
                      type="number"
                      value={topicForm.crossPollinationIntervalDays}
                    />
                  </label>
                  <label>
                    Group size
                    <input
                      min="1"
                      onChange={(event) =>
                        setTopicForm((current) => ({
                          ...current,
                          groupCapacity: event.target.value,
                        }))
                      }
                      step="1"
                      type="number"
                      value={topicForm.groupCapacity}
                    />
                  </label>
                  <label>
                    Seed bullets (one per line)
                    <textarea
                      onChange={(event) =>
                        setTopicForm((current) => ({
                          ...current,
                          seedBullets: event.target.value,
                        }))
                      }
                      placeholder={
                        "Pro: faster decisions\nPro: clearer accountability\n" +
                        "Con: less deliberation\nCon: minority voices drowned out"
                      }
                      rows={4}
                      value={topicForm.seedBullets}
                    />
                  </label>
                  <button type="submit">Create</button>
                </form>
              ) : null}
            </div>
            {pastTopics.length > 0 ? (
              <>
                <div className="admin-topic-divider">
                  <span>Past topics</span>
                </div>
                {pastTopics.map((item) => (
                  <TopicAdminCard
                    editForm={editForms[item.topic.id] ?? emptyTopicEndForm}
                    isEditingEnd={false}
                    item={item}
                    key={item.topic.id}
                    minimumEndDate={minimumEndDate}
                    onEditChange={(form) =>
                      setEditForms((current) => ({ ...current, [item.topic.id]: form }))
                    }
                    onEditEndStart={() => setEditingEndTopicId(item.topic.id)}
                    onGenerateCover={() => generateCover(item.topic.id)}
                    onLoadMessages={loadMessages}
                    onUpdate={() => requestUpdateTopic(item.topic.id)}
                  />
                ))}
              </>
            ) : null}
          </section>

          <TranscriptPanel group={selectedGroup} messages={messages} />
          <ConfirmationDialog
            confirmation={pendingConfirmation}
            onCancel={cancelConfirmation}
            onConfirm={confirmPendingAction}
          />
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
  isEditingEnd,
  item,
  minimumEndDate,
  onEditChange,
  onEditEndStart,
  onGenerateCover,
  onLoadMessages,
  onUpdate,
}: {
  editForm: TopicEndFormState;
  isEditingEnd: boolean;
  item: AdminTopicOverview;
  minimumEndDate: string;
  onEditChange: (form: TopicEndFormState) => void;
  onEditEndStart: () => void;
  onGenerateCover: () => void;
  onLoadMessages: (group: AdminGroupOverview) => void;
  onUpdate: () => void;
}) {
  function saveOnEnter(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      event.currentTarget.blur();
    }
  }

  return (
    <article className="admin-topic-card">
      <div className="admin-topic-header">
        <div>
          <p className="eyebrow">{item.topic.status}</p>
          {isEditingEnd ? null : (
            <>
              <h2>{item.topic.title}</h2>
              <p>{item.topic.description ?? "No description set."}</p>
            </>
          )}
          <div className="admin-end-date">
            {item.topic.status === "closed" ? (
              <p className="admin-muted">
                Ended: {formatDate(item.topic.closes_at)} · Cross-pollination every{" "}
                {secondsToDaysInput(item.topic.cross_pollination_interval_seconds)} day(s) ·{" "}
                Group size {item.topic.group_capacity}
              </p>
            ) : isEditingEnd ? (
              <div className="admin-inline-form">
                <label>
                  Title
                  <input
                    onChange={(event) =>
                      onEditChange({ ...editForm, title: event.target.value })
                    }
                    onKeyDown={saveOnEnter}
                    type="text"
                    value={editForm.title}
                  />
                </label>
                <label>
                  Description
                  <textarea
                    onChange={(event) =>
                      onEditChange({ ...editForm, description: event.target.value })
                    }
                    placeholder="Add a curiosity hook — one detail that makes participants want to weigh in."
                    value={editForm.description}
                  />
                </label>
                <label>
                  Expected end
                  <input
                    autoFocus
                    min={minimumEndDate}
                    onChange={(event) =>
                      onEditChange({ ...editForm, closesAt: event.target.value })
                    }
                    onKeyDown={saveOnEnter}
                    type="datetime-local"
                    value={editForm.closesAt}
                  />
                </label>
                <label>
                  Cross-pollination interval (days)
                  <input
                    min="0.01"
                    onChange={(event) =>
                      onEditChange({
                        ...editForm,
                        crossPollinationIntervalDays: event.target.value,
                      })
                    }
                    onKeyDown={saveOnEnter}
                    step="0.01"
                    type="number"
                    value={editForm.crossPollinationIntervalDays}
                  />
                </label>
                <label>
                  Group size
                  <input
                    min="1"
                    onChange={(event) =>
                      onEditChange({ ...editForm, groupCapacity: event.target.value })
                    }
                    onKeyDown={saveOnEnter}
                    step="1"
                    type="number"
                    value={editForm.groupCapacity}
                  />
                </label>
                <label>
                  Seed bullets (one per line)
                  <textarea
                    onChange={(event) =>
                      onEditChange({ ...editForm, seedBullets: event.target.value })
                    }
                    placeholder="Pro/con prompts posted into each new group when it spins up."
                    rows={4}
                    value={editForm.seedBullets}
                  />
                </label>
                <button onClick={onUpdate} type="button">
                  Save
                </button>
              </div>
            ) : (
              <p className="admin-muted">
                Expected end: {formatDate(item.topic.closes_at)} · Cross-pollination every{" "}
                {secondsToDaysInput(item.topic.cross_pollination_interval_seconds)} day(s) ·{" "}
                Group size {item.topic.group_capacity}
                <button
                  aria-label={`Edit topic schedule for ${item.topic.title}`}
                  className="admin-icon-button"
                  onClick={onEditEndStart}
                  type="button"
                >
                  edit
                </button>
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="admin-cover-actions">
        {item.topic.cover_image_url ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img alt="Cover preview" className="admin-cover-preview" src={item.topic.cover_image_url} />
        ) : null}
        <button className="admin-text-button" onClick={onGenerateCover} type="button">
          {item.topic.cover_image_url ? "Regenerate cover" : "Generate cover"}
        </button>
      </div>

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

function ConfirmationDialog({
  confirmation,
  onCancel,
  onConfirm,
}: {
  confirmation: PendingConfirmation | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  if (!confirmation) {
    return null;
  }
  const copy =
    confirmation.kind === "create-topic"
      ? {
          body: "Creating a new topic will close the current active topic because only one topic can be active at a time.",
          confirm: "Create topic",
          title: "Replace active topic?",
        }
      : {
          body: "Updating this topic will change what participants see immediately, including any new deliberation end date or summarization cadence.",
          confirm: "Update topic",
          title: "Update topic?",
        };

  return (
    <div className="admin-modal-backdrop" role="presentation">
      <section aria-modal="true" className="admin-modal" role="dialog">
        <h2>{copy.title}</h2>
        <p>{copy.body}</p>
        <div className="admin-modal-actions">
          <button className="admin-text-button" onClick={onCancel} type="button">
            Cancel
          </button>
          <button onClick={onConfirm} type="button">
            {copy.confirm}
          </button>
        </div>
      </section>
    </div>
  );
}
