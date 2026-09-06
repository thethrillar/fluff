from dataclasses import dataclass

from model.StarboardQueueStatus import StarboardQueueStatus


@dataclass
class StarboardQueue:
    message_id: int              # the message ID of the starred message
    channel_id: int              # the channel where this message lives
    queue_message_id: int | None # the message in the starboard queue channel for approving/denying the message
    status: StarboardQueueStatus # enum for the status of the message in the starboard queue, e.g. submitted, accepted, rejected, etc