-- Pending kicks
CREATE TABLE pending_kicks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    kick_after_unix_time INTEGER,
    unless_has_role_id INTEGER  -- can be null for unconditional kick
);
