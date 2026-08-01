from dataclasses import dataclass


@dataclass
class LeaderboardEntry:
    user_id: int #the users discord ID
    user_name: str #the users discord name
    completion_time: int #how long, in seconds, the user took to finish
    completion_date: int #the date, in epoch format, when the user attained this entry