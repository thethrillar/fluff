CREATE TABLE starboard_queue (
    message_id TEXT PRIMARY KEY, --message that may potentially be posted to starboard
    channel_id TEXT NOT NULL, --the channel where this message lives
    queue_message_id TEXT, --the message in the starboard queue channel for approving/denying the message
    status TEXT NOT NULL
) STRICT;