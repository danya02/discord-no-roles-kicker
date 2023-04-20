-- Guild members and when they joined
CREATE TABLE new_members(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    joined_at_unix_time INTEGER,
    is_considered_for_kicking INTEGER  -- boolean
);
