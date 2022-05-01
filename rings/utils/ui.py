import discord


class Confirm(discord.ui.View):
    def __init__(self, confirm_msg="Confirmed", cancel_msg="Cancelled", *, timeout=180):
        super().__init__(timeout=timeout)
        self.value = None
        self.confirm_msg = confirm_msg
        self.cancel_msg = cancel_msg
        self.message = None

    async def on_timeout(self):
        self.value = False
        self.stop()
        self.clear_items()
        await self.message.edit(
            content=f":negative_squared_cross_mark: | Interaction has expireded, please answer within **{self.timeout}** seconds.",
            view=self,
        )

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.value = True
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content=self.confirm_msg, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content=self.cancel_msg, view=self)


async def paginate(ctx, entries, page_size, embed_maker, *, timeout=300):
    paginator = Paginator(embed_maker, page_size, entries, timeout=timeout)
    paginator.message = await ctx.send(
        embed=paginator.embed_maker(paginator, paginator.get_entry_subset()),
        view=paginator,
    )
    await paginator.wait()


class Paginator(discord.ui.View):
    def __init__(self, embed_maker, page_size, entries, *, timeout=180):
        super().__init__(timeout=timeout)

        self.embed_maker = embed_maker
        self.entries = entries
        self.index = 0
        self.max_index = max(0, ((len(entries) - 1) // page_size))
        self.page_size = page_size

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(view=self)

    def get_entry_subset(self):
        subset = self.entries[
            self.index * self.page_size : (self.index + 1) * self.page_size
        ]
        return subset[0] if self.page_size == 1 else subset

    @discord.ui.button(label="First", style=discord.ButtonStyle.secondary)
    async def first_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.index = 0
        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.index - 1 < 0:
            self.index = self.max_index
        else:
            self.index -= 1

        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.index + 1 > self.max_index:
            self.index = 0
        else:
            self.index += 1

        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )

    @discord.ui.button(label="Last", style=discord.ButtonStyle.secondary)
    async def last_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.index = self.max_index
        await interaction.response.edit_message(
            embed=self.embed_maker(self, self.get_entry_subset()), view=self
        )
