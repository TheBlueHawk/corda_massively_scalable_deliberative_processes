ALTER TABLE topics
    ADD COLUMN IF NOT EXISTS cross_pollination_interval_seconds INT NOT NULL DEFAULT 86400;

ALTER TABLE topics
    ADD COLUMN IF NOT EXISTS next_cross_pollination_at TIMESTAMPTZ;

UPDATE topics
SET next_cross_pollination_at =
    created_at + make_interval(secs => cross_pollination_interval_seconds)
WHERE status = 'active'
    AND next_cross_pollination_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_topics_cross_pollination_due
    ON topics(status, next_cross_pollination_at);
