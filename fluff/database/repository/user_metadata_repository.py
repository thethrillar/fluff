from database.database import Database

"""Repository class responsible for handling any reads and writes to the user_metadata table"""
class UserMetadataRepository:
    def __init__(self, db: Database):
        self.db = db

    async def update_user_metadata(self, user_id: int, name: str) -> None:
        """Updates the user_metadata table"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "INSERT INTO user_metadata (id, name) "
                "VALUES (?, ?) "
                "ON CONFLICT (id) DO UPDATE SET "
                "name = ? "
                "WHERE name != ?",
                (str(user_id), name, name, name),
            )
            await conn.commit()

    async def update_users_metadata(self, updates: list[tuple[int, str]]) -> None:
        """Updates the user_metadata table for multiple (user_id, name) pairs"""
        async with self.db.get_write_connection() as conn:
            await conn.executemany(
                "INSERT INTO user_metadata (id, name) "
                "VALUES (?, ?) "
                "ON CONFLICT (id) DO UPDATE SET "
                "name = ? "
                "WHERE name != ?",
                [(str(uid), name, name, name) for uid, name in updates],
            )
            await conn.commit()