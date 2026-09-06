import sqlite3

import discord
from discord import TextChannel
from discord.ext.commands import Cog

from database.model.StarboardQueue import StarboardQueue
from database.repository.starboard_queue_repository import StarboardQueueRepository
from helpers.message_link_embed import build_message_embed
from view.StarboardApprovalView import StarboardApprovalView

STAR_EMOJI = "⭐"
STAR_EMOJI_COUNT_THRESHOLD = 5
class Starboard(Cog):
    """Handles publishing starboard messages.

    When a message receives 5 star emoji reactions, the message is sent to the starboard queue channel.
    This channel allows staff members to either deny the starboard request, or accept the starboard request,
    in which case the message is automatically sent to the configured public starboard channel."""
    def __init__(self, bot):
        self.bot = bot
        self.starboard_queue_repo: StarboardQueueRepository = StarboardQueueRepository(self.bot.db)

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload is None or payload.guild_id is None or payload.channel_id is None or payload.message_id is None or payload.emoji is None or payload.member is None or payload.member.bot:
            return

        if str(payload.emoji) != STAR_EMOJI:
            return

        queue_channel_id: int = self.bot.config_service.get_server_config(payload.guild_id, "starboard", "queue_channel")
        starboard_channel_id: int = self.bot.config_service.get_server_config(payload.guild_id, "starboard", "starboard_channel")
        if queue_channel_id is None or starboard_channel_id is None:
            return

        queue_channel_id = int(queue_channel_id)

        try:
            starboard_queue_entry: StarboardQueue | None = await self.starboard_queue_repo.get_starboard_queue_entry_by_id(payload.message_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get starboard queue entry for message ID {payload.message_id}: {err}")
            return

        if starboard_queue_entry is not None:
            return

        channel = await self.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException as e:
            self.bot.log.error(f"Failed to fetch message {payload.message_id}: {e}")
            return

        if not message or not message.reactions:
            return

        star_emoji_count = 0
        for reaction in message.reactions:
            if reaction.emoji == STAR_EMOJI:
                star_emoji_count = reaction.count
                break

        if star_emoji_count < STAR_EMOJI_COUNT_THRESHOLD:
            return

        try:
            starboard_queue_entry: StarboardQueue | None = await self.starboard_queue_repo.add_starboard_queue_entry(payload.message_id, channel.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to create starboard queue entry for message ID {payload.message_id}: {err}")
            return

        if starboard_queue_entry is None:
            return

        queue_channel: TextChannel = await self.get_channel(queue_channel_id)
        if queue_channel is None:
            return

        view = StarboardApprovalView(self.bot)
        embeds: list[discord.Embed] = await build_message_embed(message)
        queue_message = await queue_channel.send(embeds=embeds, view=view)

        try:
            await self.starboard_queue_repo.update_queue_message_id(payload.message_id, queue_message.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to update starboard queue entry for message ID {payload.message_id}: {err}")

    async def get_channel(self, channel_id: int) -> TextChannel | None:
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException as e:
                self.bot.log.error(f"Failed to fetch channel {channel_id}: {e}")
                return None

        return channel


async def setup(bot):
    await bot.add_cog(Starboard(bot))
    bot.add_view(StarboardApprovalView(bot))
