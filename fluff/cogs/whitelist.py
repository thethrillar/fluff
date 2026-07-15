import asyncio
import sqlite3
from typing import Optional

import discord
from discord import User
from discord.ext import commands
from discord.ext.commands import Cog

from database.repository.whitelist_ping_repository import WhitelistPingRepository
from helpers.embeds import stock_embed
from converter.mention_or_id_converter import MentionOrIDUser, MentionOrIDMember
import io

MAX_CHARACTERS_PER_EMBED = 980

"""Whitelist Cog which allows users to add other users to their ping whitelist. This prevents any whitelisted users
from receiving ping violations."""
class Whitelist(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.whitelist_ping_repo: WhitelistPingRepository = WhitelistPingRepository(self.bot.db)

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
        whitelisted_users = list()
        user_id = user.id if user else ctx.author.id
        try:
            whitelisted_users = await self.whitelist_ping_repo.get_whitelisted_users(user_id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get whitelisted users for user ID {user_id}: {err}")
            return await ctx.reply(content="Unable to get whitelisted users", mention_author=False)

        if not whitelisted_users:
            if user_id == ctx.author.id:
                return await ctx.reply(
                    content="You have not whitelisted any users yet. Use `pls whitelist add` to add users to your whitelist.",
                    mention_author=False)
            else:
                return await ctx.reply(
                    content="This user has not whitelisted any users yet.",
                    mention_author=False)

        user_name = user.display_name if user else ctx.author.display_name

        #user_ids = [1038816143940530247,1062334226231480432,1078749844123947058,1109940833505001583,1134683256638410782,1137130059212259388,1139568311034712106,1146981580997406864,1177624565858435213,1184296536360894486,1187563144705486898,1235521932032610306,1238180352183505031,1288561357943472209,1315691673199579137,1337241076750225458,1340981794799091742,1344752485004345344,1347698819684634745,1354032756136480821,1371919145926525131,1374539269397545000,1384491742891474944,1385801358598213703,1387110540484280380,1389002244753588419,1414024164368711781,1427350718792339547,1436425537378717727,1457743956233162814,1475653092178657312,1476744731923841025,1483273693034446988,1487114621297889411,1488114257424941159,1492602639442116648,167093492424769538,212719295124209664,236210278025396224,307312147430637568,308949254225920001,363810458492469258,369532049989828608,450447141136236555,474434185864675328,487360805898027008,710991863804592158,762330705358880770,792935043466526761,861356914759696455,930534872991297607,944243530140880947,951308529577361479,956842100413059072,962200353095426078,966264898717876304,993614975803347139]
        #for user_id_test in user_ids:
        #    testuser = await self.bot.fetch_user(user_id_test)
        #    if testuser is not None:
        #        self.bot.log.info(f"{user_id_test}, {testuser.name}")
        #    await asyncio.sleep(1)

        #return await self.create_and_send_whitelist_embed(f"Whitelisted users for {user_name}", f"whitelisted-users-{user_id}", ctx, whitelisted_users)
        return await self.create_and_send_whitelist_embed2(ctx, f"Whitelisted users for {user_name}", whitelisted_users)

    @whitelist.command()
    @commands.guild_only()
    async def check(self, ctx: commands.Context):
        """Returns all users who have the author in their whitelist"""
        users_who_have_whitelisted_author = list()
        try:
            users_who_have_whitelisted_author = await self.whitelist_ping_repo.get_users_who_whitelisted_user(ctx.author.id)
        except sqlite3.Error as err:
            self.bot.log.error(f"Failed to get users who have whitelisted user ID {ctx.author.id}: {err}")
            return await ctx.reply(content="Unable to get users who have whitelisted you", mention_author=False)

        if not users_who_have_whitelisted_author:
            return await ctx.reply(
                content="No one has whitelisted you yet.",
                mention_author=False)

        return await self.create_and_send_whitelist_embed2(ctx, f"Users who have whitelisted {ctx.author.display_name}", users_who_have_whitelisted_author)

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

    async def create_and_send_whitelist_embed(self, embed_title: str, file_title: str, ctx: commands.Context, user_ids: list[int]):
        """Constructs the embed consisting of the users that are whitelisted, and sends the response"""
        embed = stock_embed(self.bot)
        embed.color = discord.Color.light_embed()
        embed.title = embed_title

        partitioned_user_mentions = self.partition_user_mentions(user_ids)
        for user_mention in partitioned_user_mentions:
            embed.add_field(
                name="",
                value=user_mention,
                inline=False,
            )

        # length of embed can have no more than 6000 characters in it. That is somewhere above 200 people in a users whitelist.
        # length of partitioned_user_mentions would require the user to have over 1000 people in their whitelist,
        # so that is very unlikely.
        if len(embed) > 6000 or len(partitioned_user_mentions) > 25:
            file_content = ""
            for user_mention in partitioned_user_mentions:
                file_content += user_mention + "\n"
            await ctx.send(
                file=discord.File(
                    io.StringIO(file_content),  # type:ignore
                    filename=f"{file_title}.txt",
                )
            )
        else:
            await ctx.reply(embed=embed, mention_author=False)

    async def create_and_send_whitelist_embed2(self, ctx: commands.Context, title: str, user_ids: list[tuple[int, str]]):
        entries = []
        for uid, name in user_ids:
            entries.append((uid, discord.utils.escape_markdown(name)))
            #member = ctx.guild.get_member(uid)
            #compare here and replace in db if different
            #if member:
            #    entries.append((uid, member.name))
            #else:
                #replace with username from DB here
            #    entries.append((uid, 'abcdefghijklmnopqrstuvwxyzaaaaaaaaaa'))

        view = WhitelistTextPaginator(entries, title, ctx.author.id)
        embeddd = view.build_embed()
        self.bot.log.info(f"embed size: {len(embeddd)}")
        msg = await ctx.reply(
            embed=embeddd,
            view=view if view.max_page > 0 else None,
            mention_author=False,
        )
        if view.max_page > 0:
            view.message = msg

    def partition_user_mentions(self, user_ids: list[int]) -> list[str]:
        """Partitions user ID's into a list of user mentions. A discord embed only allows up to 1024 characters.
        Any more than that, and we get an error. This method splits up user mentions into a list so that we can create
        multiple embeds, if necessary.

        Returns: a list of user mentions, where each string in the list is made up of multiple comma separated user
        mentions"""
        partitions = []
        current = []
        current_len = 0

        for user_id in user_ids:
            mention = f"<@{user_id}>"
            # + 3 for " | "
            characters_added = len(mention) + 3
            if current_len + characters_added > MAX_CHARACTERS_PER_EMBED:
                partitions.append(' | '.join(current))
                current = [mention]
                current_len = characters_added
            else:
                current.append(mention)
                current_len += characters_added

        if current:
            partitions.append(' | '.join(current))

        return partitions

async def setup(bot):
    await bot.add_cog(Whitelist(bot))

ENTRIES_PER_PAGE = 20
class WhitelistTextPaginator(discord.ui.View):
    def __init__(self, entries: list[tuple[int, str]], title: str, author_id: int):
        super().__init__(timeout=180)
        self.entries = entries  # (user_id, username)
        self.title = title
        self.author_id = author_id
        self.index = 0
        self.max_page = (len(entries) - 1) // ENTRIES_PER_PAGE
        self.message: discord.Message | None = None  # set this after sending
        self._update_buttons()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    def _update_buttons(self):
        self.previous_page.disabled = self.index == 0
        self.next_page.disabled = self.index == self.max_page

    def build_embed(self) -> discord.Embed:
        start = self.index * ENTRIES_PER_PAGE
        page_entries = self.entries[start:start + ENTRIES_PER_PAGE]

        #lines = [f"**{i + 1}.** {username} - `{user_id}`" for i, (user_id, username) in enumerate(page_entries, start=start)]
        #lines = [f"**{i + 1}.** {username} - <@{user_id}>" for i, (user_id, username) in enumerate(page_entries, start=start)]
        lines = [f"**{i + 1}.** <@{user_id}> ({username})" for i, (user_id, username) in enumerate(page_entries, start=start)]

        embed = discord.Embed(
            title=self.title,
            description="\n".join(lines),
            color=discord.Color.light_embed(),
        )
        embed.set_footer(text=f"Page {self.index + 1}/{self.max_page + 1} • {len(self.entries)} total")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            return False
        return True

    @discord.ui.button(label="🔢", style=discord.ButtonStyle.primary)
    async def jump_to_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PageSelectModal(self))

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)


class PageSelectModal(discord.ui.Modal, title="Jump to Page"):
    def __init__(self, paginator_view: "WhitelistTextPaginator"):
        super().__init__()
        self.paginator_view = paginator_view

        self.page_input = discord.ui.TextInput(
            label=f"Page number (1-{paginator_view.max_page + 1})",
            placeholder="e.g. 3",
            min_length=1,
            max_length=len(str(paginator_view.max_page + 1)),
            required=True,
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.page_input.value.strip()

        if not raw.isdigit():
            return await interaction.response.send_message("That's not a valid page number.", ephemeral=True)

        page = int(raw)
        if page < 1 or page > self.paginator_view.max_page + 1:
            return await interaction.response.send_message(
                f"Page must be between 1 and {self.paginator_view.max_page + 1}.",
                ephemeral=True,
            )

        self.paginator_view.index = page - 1
        self.paginator_view._update_buttons()
        await interaction.response.edit_message(embed=self.paginator_view.build_embed(), view=self.paginator_view)
