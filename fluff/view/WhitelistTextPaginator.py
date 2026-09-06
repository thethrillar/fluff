import discord

ENTRIES_PER_PAGE = 20
class WhitelistTextPaginator(discord.ui.View):
    """Paginator class responsible for handling all pagination duties for whitelist embed"""
    def __init__(self, page_fetcher, count_fetcher, target_user_id: int, title: str, author_id: int):
        super().__init__(timeout=300)
        self.page_fetcher = page_fetcher    # e.g. self.repo.get_whitelisted_users_page
        self.count_fetcher = count_fetcher  # e.g. self.repo.get_whitelisted_users_count
        self.target_user_id = target_user_id
        self.title = title
        self.author_id = author_id
        self.index = 0
        self.total_count = 0
        self.max_page = 0
        self.message: discord.Message | None = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    def _update_buttons(self):
        """disables buttons if out of range of valid pages"""
        self.previous_page.disabled = self.index == 0
        self.next_page.disabled = self.index == self.max_page

    async def build_embed(self) -> discord.Embed:
        """Builds the actual embed by fetching data from database"""
        self.total_count = await self.count_fetcher(self.target_user_id)
        self.max_page = max((self.total_count - 1) // ENTRIES_PER_PAGE, 0)
        self.index = min(self.index, self.max_page)  # clamp if data shrank

        start = self.index * ENTRIES_PER_PAGE
        page_entries = await self.page_fetcher(self.target_user_id, start, ENTRIES_PER_PAGE)

        lines = [
            f"**{i + 1}.** <@{user_id}> ({discord.utils.escape_markdown(username)})"
            for i, (user_id, username) in enumerate(page_entries, start=start)
        ]

        embed = discord.Embed(
            title=self.title,
            description="\n".join(lines) if lines else "No entries.",
            color=discord.Color.light_embed(),
        )
        embed.set_footer(text=f"Page {self.index + 1}/{self.max_page + 1} • {self.total_count} total")
        self._update_buttons()
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures that only the user who invoked the command to create this embed can change the pages"""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the user who invoked this command can change the pages.", ephemeral=True)
            return False

        return True

    @discord.ui.button(label="🔢", style=discord.ButtonStyle.primary)
    async def jump_to_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PageSelectModal(self))

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        await interaction.response.edit_message(embed=await self.build_embed(), view=self)

class PageSelectModal(discord.ui.Modal, title="Jump to Page"):
    """Page select modal that handles jumping to a specific whitelist page"""
    def __init__(self, paginator_view: WhitelistTextPaginator):
        super().__init__()
        self.paginator_view = paginator_view

        self.page_input = discord.ui.TextInput(
            label=f"Page number (1-{paginator_view.max_page + 1})",
            placeholder="e.g. 3",
            required=True,
        )
        self.add_item(self.page_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.page_input.value.strip()
        if not raw.isdigit() or not (1 <= int(raw) <= self.paginator_view.max_page + 1):
            return await interaction.response.send_message(
                f"Enter a page number between 1 and {self.paginator_view.max_page + 1}.",
                ephemeral=True,
            )

        self.paginator_view.index = int(raw) - 1
        await interaction.response.edit_message(
            embed=await self.paginator_view.build_embed(), view=self.paginator_view
        )