from database.database import Database
from database.model.LeaderboardEntry import LeaderboardEntry

"""Repository class responsible for handling any reads and writes to the rule push leaderboard table"""
class RulePushLeaderboardRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_rule_push_leaderboard(self) -> list[LeaderboardEntry]:
        """Fetches all rule push leaderboard entries"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT rpl.user_id, COALESCE(um.name, 'Unknown Name') AS name, rpl.completion_time, rpl.completion_date "
                "FROM rule_push_leaderboard rpl "
                "LEFT JOIN user_metadata um "
                "ON rpl.user_id = um.id "
                "ORDER BY rpl.completion_time ASC, rpl.completion_date ASC "
                "LIMIT 20"
            )
            rows = await cursor.fetchall()

        leaderboard_entries: list[LeaderboardEntry] = []
        for row in rows:
            user_id, name, completion_time, completion_date = row
            user_id = int(user_id)
            completion_time = int(completion_time)
            completion_date = int(completion_date)
            leaderboard_entries.append(LeaderboardEntry(user_id, name, completion_time, completion_date))

        return leaderboard_entries

    async def update_rule_push_leaderboard(self, user_id: int, completion_time: int, completion_date: int) -> None:
        """Updates the rule_push_leaderboard table"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "INSERT INTO rule_push_leaderboard (user_id, completion_time, completion_date) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "completion_time = ?, completion_date = ? "
                "WHERE completion_time > ?",
                (str(user_id), completion_time, completion_date, completion_time, completion_date, completion_time),
            )

            await conn.execute(
                "DELETE FROM rule_push_leaderboard "
                "WHERE user_id NOT IN "
                "(SELECT user_id FROM rule_push_leaderboard "
                "ORDER BY completion_time ASC, completion_date ASC "
                "LIMIT 20)"
            )

            await conn.commit()