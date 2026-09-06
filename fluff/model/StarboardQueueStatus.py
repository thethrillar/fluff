from enum import StrEnum, auto

class StarboardQueueStatus(StrEnum):
    """Enumeration of possible statuses for an entry in the starboard queue"""
    CREATED = auto() #this entry was created in the database, but not submitted to the starboard queue channel
    SUBMITTED = auto() #this entry was submitted to the starboard queue channel
    ACCEPTED = auto() #this entry was accepted, and was posted to the public starboard channel
    REJECTED = auto() #this entry was rejected, and will not be posted to the public starboard channel