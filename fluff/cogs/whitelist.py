import sqlite3
from typing import Optional

import discord
from discord.ext import commands
from discord.ext.commands import Cog

from database.model.TempBannedUser import TempBannedUser
from database.repository.tempban_repository import TempBanRepository
from database.repository.user_metadata_repository import UserMetadataRepository
from database.repository.whitelist_ping_repository import WhitelistPingRepository
from converter.mention_or_id_converter import MentionOrIDUser, MentionOrIDMember
from view.WhitelistTextPaginator import WhitelistTextPaginator

"""Whitelist Cog which allows users to add other users to their ping whitelist. This prevents any whitelisted users
from receiving ping violations."""
class Whitelist(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.whitelist_ping_repo: WhitelistPingRepository = WhitelistPingRepository(self.bot.db)
        self.user_metadata_repo: UserMetadataRepository = UserMetadataRepository(self.bot.db)
        self.tempban_repo: TempBanRepository = TempBanRepository(self.bot.db)

    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    @commands.group(invoke_without_command=True)
    async def whitelist(self, ctx: commands.Context, user: Optional[MentionOrIDUser] = None):
        """Display whitelisted users.

        Please note that whitelisting only applies if you have the whitelist ping role.
        Available commands:
        pls whitelist\npls whitelist add user1, user2, etc\npls whitelist remove user1, user2, etc
        pls whitelist user\n pls whitelist check

        - `user`
        The user whose whitelist you would like to check. Optional. returns your own whitelist if no user is passed
        """
        count = 0
        user_id = user.id if user else ctx.author.id
        try:
            count = await self.whitelist_ping_repo.get_whitelisted_users_count(user_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get whitelisted users for user ID {user_id}: {err}")
            return await ctx.reply(content="Unable to get whitelisted users", mention_author=False)

        if count == 0:
            if user_id == ctx.author.id:
                return await ctx.reply(
                    content="You have not whitelisted any users yet. Use `pls whitelist add` to add users to your whitelist.",
                    mention_author=False)
            else:
                return await ctx.reply(
                    content="This user has not whitelisted any users yet.",
                    mention_author=False)

        user_name = user.display_name if user else ctx.author.display_name
        return await self.send_whitelisted_by_user_embed(ctx, user_id, user_name)

    @whitelist.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def check(self, ctx: commands.Context):
        """Returns all users who have the author in their whitelist"""
        count = 0
        try:
            count = await self.whitelist_ping_repo.get_users_who_whitelisted_user_count(ctx.author.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get users who have whitelisted user ID {ctx.author.id}: {err}")
            return await ctx.reply(content="Unable to get users who have whitelisted you", mention_author=False)

        if count == 0:
            return await ctx.reply(
                content="No one has whitelisted you yet.",
                mention_author=False)

        return await self.send_whitelisted_this_user_embed(ctx, ctx.author.id, ctx.author.display_name)

    @whitelist.command()
    @commands.guild_only()
    async def add(self, ctx: commands.Context, members: commands.Greedy[MentionOrIDMember]):
        """Adds a list of members to the users whitelist."""
        if not members:
            return await ctx.reply(content="Please include at least one valid user ID or user mention",
                                   mention_author=False)

        user_ids_to_whitelist: list[tuple[int, str]] = list()
        for member in members:
            if member.id == ctx.author.id:
                return await ctx.reply(content="Cannot add yourself to your whitelist", mention_author=False)
            if member.bot:
                return await ctx.reply(content="Bots cannot be added to your whitelist", mention_author=False)
            user_ids_to_whitelist.append((member.id, member.name))
        inserted = 0
        try:
            await self.user_metadata_repo.update_users_metadata(user_ids_to_whitelist)
            inserted = await self.whitelist_ping_repo.add_whitelisted_users(ctx.author.id, user_ids_to_whitelist)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to add whitelisted users for {ctx.author.id}: {err}")
            return await ctx.reply(
                content="Unable to add users to your whitelist. Make sure you aren't trying to whitelist someone who you have already whitelisted.",
                mention_author=False)

        if inserted == 0:
            return await ctx.reply(content=f"No users added to your whitelist", mention_author=False)

        return await ctx.reply(content=f"{inserted} users added to your whitelist", mention_author=False)

    @whitelist.command()
    @commands.guild_only()
    async def remove(self, ctx: commands.Context, members: commands.Greedy[MentionOrIDUser]):
        """Removes a list of members from the users whitelist."""
        if not members:
            return await ctx.reply(content="Please include at least one valid user ID or user mention",
                                   mention_author=False)

        user_ids_to_remove = [member.id for member in members]
        user_ids_deleted: int = 0
        try:
            user_ids_deleted = await self.whitelist_ping_repo.remove_whitelisted_users(ctx.author.id, user_ids_to_remove)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to remove whitelisted users for {ctx.author.id}: {err}")
            return await ctx.reply(
                content="Unable to remove users from your whitelist.",
                mention_author=False)

        if user_ids_deleted == len(user_ids_to_remove):
            return await ctx.reply(content=f"{user_ids_deleted} users removed from your whitelist",
                                   mention_author=False)
        else:
            return await ctx.reply(content=f"Removed {user_ids_deleted}/{len(user_ids_to_remove)} mentioned users. Some users were not in your whitelist",
                                   mention_author=False)


    async def send_whitelisted_by_user_embed(self, ctx: commands.Context, target_user_id: int, name: str):
        """Sends embed containing users who this user has whitelisted"""
        view = WhitelistTextPaginator(
            page_fetcher=self.whitelist_ping_repo.get_whitelisted_users_page,
            count_fetcher=self.whitelist_ping_repo.get_whitelisted_users_count,
            target_user_id=target_user_id,
            title=f"Whitelisted Users for {name}",
            author_id=ctx.author.id,
        )
        embed = await view.build_embed()
        msg = await ctx.reply(embed=embed, view=view if view.max_page > 0 else None, mention_author=False)
        if view.max_page > 0:
            view.message = msg

    async def send_whitelisted_this_user_embed(self, ctx: commands.Context, target_user_id: int, name: str):
        """Sends embed containing users who this user has been whitelisted by"""
        view = WhitelistTextPaginator(
            page_fetcher=self.whitelist_ping_repo.get_users_who_whitelisted_user_page,
            count_fetcher=self.whitelist_ping_repo.get_users_who_whitelisted_user_count,
            target_user_id=target_user_id,
            title=f"Users who have whitelisted {name}",
            author_id=ctx.author.id,
        )
        embed = await view.build_embed()
        msg = await ctx.reply(embed=embed, view=view if view.max_page > 0 else None, mention_author=False)
        if view.max_page > 0:
            view.message = msg

    @Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User | discord.Member):
        if user is None or user.id is None:
            return

        banned_user_info: TempBannedUser | None = await self.tempban_repo.get_banned_user_info(user.id, guild.id)
        if banned_user_info is not None:
            return

        try:
            await self.whitelist_ping_repo.remove_from_all_whitelists(user.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Error removing user {user.id} from whitelists: {err}")

async def setup(bot):
    await bot.add_cog(Whitelist(bot))