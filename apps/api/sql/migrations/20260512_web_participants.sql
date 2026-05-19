-- Web participant identity replacing Telegram user identity.

CREATE TABLE participants (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    display_name TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Groups can now be purely web-based (no Telegram forum topic).
ALTER TABLE groups
    ALTER COLUMN thread_id   DROP NOT NULL,
    ALTER COLUMN invite_link DROP NOT NULL;

ALTER TABLE groups DROP CONSTRAINT IF EXISTS groups_thread_id_key;

CREATE UNIQUE INDEX groups_thread_id_unique ON groups (thread_id)
    WHERE thread_id IS NOT NULL;

-- Memberships: swap composite PK for a surrogate UUID so both Telegram and web
-- participants can coexist in the table during any future migration period.
ALTER TABLE memberships DROP CONSTRAINT memberships_pkey;

ALTER TABLE memberships
    ADD COLUMN id             UUID DEFAULT gen_random_uuid(),
    ALTER COLUMN telegram_user_id DROP NOT NULL,
    ADD COLUMN participant_id UUID REFERENCES participants(id) ON DELETE CASCADE;

ALTER TABLE memberships ADD PRIMARY KEY (id);

ALTER TABLE memberships
    ADD CONSTRAINT membership_has_identity
    CHECK (telegram_user_id IS NOT NULL OR participant_id IS NOT NULL);

CREATE UNIQUE INDEX memberships_participant_group
    ON memberships (participant_id, group_id)
    WHERE participant_id IS NOT NULL;

-- thread_messages: add UUID surrogate PK; make Telegram columns nullable so
-- web-originated messages can be stored without any Telegram identifiers.
ALTER TABLE thread_messages DROP CONSTRAINT thread_messages_pkey;

ALTER TABLE thread_messages
    ADD COLUMN id             UUID        NOT NULL DEFAULT gen_random_uuid(),
    ALTER COLUMN message_id   DROP NOT NULL,
    ALTER COLUMN thread_id    DROP NOT NULL,
    ADD COLUMN participant_id UUID REFERENCES participants(id),
    ADD COLUMN is_moderator   BOOLEAN     NOT NULL DEFAULT FALSE;

ALTER TABLE thread_messages ADD PRIMARY KEY (id);

CREATE UNIQUE INDEX thread_messages_telegram_unique
    ON thread_messages (message_id, thread_id)
    WHERE message_id IS NOT NULL AND thread_id IS NOT NULL;
