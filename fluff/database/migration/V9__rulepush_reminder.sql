--reminder table that tracks if a rulepush session has reminded the user of the time limit before
--being automatically kicked from the server
CREATE TABLE rule_push_reminder (
    session_id INTEGER PRIMARY KEY,
    reminder_sent INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES roleban_session (id) ON DELETE CASCADE
) STRICT;