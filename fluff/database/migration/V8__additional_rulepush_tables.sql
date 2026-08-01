ALTER TABLE rule ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0;
ALTER TABLE roleban_session ADD COLUMN start_time TEXT NOT NULL DEFAULT '-1'; --for rulepush leaderboard timing

CREATE TABLE user_metadata (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
) STRICT;

CREATE TABLE rule_push_leaderboard (
    user_id TEXT PRIMARY KEY,
    completion_time INTEGER NOT NULL,
    completion_date INTEGER NOT NULL
) STRICT;