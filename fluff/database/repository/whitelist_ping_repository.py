from database.database import Database

"""Repository class responsible for handling any reads and writes to the whitelist_ping table"""
class WhitelistPingRepository:
    def __init__(self, db: Database):
        self.db = db

    async def get_whitelisted_users_count(self, user_id: int) -> int:
        """Counts users this user has whitelisted"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM whitelist_ping WHERE user_id = ?",
                (str(user_id),)
            )
            row = await cursor.fetchone()
            return row[0]

    async def get_whitelisted_users_page(self, user_id: int, offset: int, limit: int) -> list[tuple[int, str]]:
        """Gets a page of users this user has whitelisted"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT wp.whitelisted_user_id, um.name "
                "FROM whitelist_ping wp LEFT JOIN "
                "user_metadata um ON wp.whitelisted_user_id = um.id "
                "WHERE wp.user_id = ? "
                "ORDER BY um.name ASC, wp.whitelisted_user_id ASC "
                "LIMIT ? OFFSET ?",
                (str(user_id), limit, offset)
            )
            return await self._rows_to_entries(cursor)

    async def get_users_who_whitelisted_user_count(self, user_id: int) -> int:
        """Counts users who have whitelisted this user"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM whitelist_ping WHERE whitelisted_user_id = ?",
                (str(user_id),)
            )
            row = await cursor.fetchone()
            return row[0]

    async def get_users_who_whitelisted_user_page(self, user_id: int, offset: int, limit: int) -> list[tuple[int, str]]:
        """Gets a page of users who have whitelisted this user"""
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT wp.user_id, um.name "
                "FROM whitelist_ping wp LEFT JOIN "
                "user_metadata um ON wp.user_id = um.id "
                "WHERE wp.whitelisted_user_id = ? "
                "ORDER BY um.name ASC, wp.user_id ASC "
                "LIMIT ? OFFSET ?",
                (str(user_id), limit, offset)
            )
            return await self._rows_to_entries(cursor)

    async def is_user_in_whitelist(self, pinged_user_id: int, pinged_by_id: int) -> bool:
        """Determines if the pinged_by user is in the pinged user's whitelist.

        Returns:
        true if the pinged_by user is in the pinged user's whitelist, false otherwise.
        """
        async with self.db.get_read_connection() as conn:
            cursor = await conn.execute(
                "SELECT EXISTS(SELECT * FROM whitelist_ping WHERE user_id = ? AND whitelisted_user_id = ?)",
                (str(pinged_user_id), str(pinged_by_id))
            )
            row = await cursor.fetchone()
            return bool(row[0])

    async def add_whitelisted_users(self, user_id: int, users_to_whitelist: list[tuple[int, str]]) -> int:
        """Adds the list of user ID's to the users whitelist"""
        async with self.db.get_write_connection() as conn:
            inserted = 0
            for user_id_to_whitelist, user_name_to_add in users_to_whitelist:
                cursor = await conn.execute(
                    "INSERT OR IGNORE INTO whitelist_ping (user_id, whitelisted_user_id) "
                    "VALUES (?,?)",
                    (str(user_id), str(user_id_to_whitelist))
                )
                inserted += cursor.rowcount
            await conn.commit()

            return inserted

    async def remove_whitelisted_users(self, user_id: int, users_to_remove: list[int]) -> int:
        """removes the list of user ID's from the users whitelist

        Returns: the number of users removed from the whitelist table for this user"""
        async with self.db.get_write_connection() as conn:
            placeholders = ",".join("?" * len(users_to_remove))
            cursor = await conn.execute(
                f"DELETE FROM whitelist_ping WHERE user_id = ? AND whitelisted_user_id IN ({placeholders})",
                (str(user_id), *[str(uid) for uid in users_to_remove])
            )
            await conn.commit()
            return cursor.rowcount

    async def remove_from_all_whitelists(self, user_id: int) -> None:
        """Removes a users whitelist, in addition to removing them from everyone elses whitelist"""
        async with self.db.get_write_connection() as conn:
            await conn.execute(
                "DELETE FROM whitelist_ping WHERE user_id = ? OR whitelisted_user_id = ?",
                (str(user_id), str(user_id))
            )
            await conn.commit()

    async def _rows_to_entries(self, cursor) -> list[tuple[int, str]]:
        rows = await cursor.fetchall()
        result: list[tuple[int, str]] = []
        for row in rows:
            whitelisted_user_id = int(row[0])
            whitelisted_user_name = row[1] or 'username unknown'
            result.append((whitelisted_user_id, whitelisted_user_name))
        return result