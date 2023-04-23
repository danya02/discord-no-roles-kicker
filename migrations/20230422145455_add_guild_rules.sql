-- Guild rules
CREATE TABLE guild_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER UNIQUE NOT NULL,
    new_member_kick_timeout INTEGER,  -- null for no kick for new members
    immunity_role_id INTEGER,  -- null for no immunity role
    loss_of_immunity_role_timeout INTEGER, -- null for no kick on loss of immunity role
    system_message_channel_id INTEGER NOT NULL,
    pending_kick_notification_channel_id INTEGER,
    pending_kick_notification_values VARCHAR(255) NOT NULL,  -- space-separated decimal integers representing seconds before kick arrives
    kick_safety_timeout INTEGER NOT NULL
);

-- Add info on the latest pending kick notification
ALTER TABLE pending_kicks ADD COLUMN latest_pending_kick_notification_sent INTEGER;
