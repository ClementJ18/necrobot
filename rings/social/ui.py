import discord


class TextInput(discord.ui.TextInput):
    async def callback(self, interaction):
        self.view.stop()
        self.view.clear_items()

        if self.value.lower() == self.view.answer:
            self.view.value = True
            await interaction.response.edit_message(
                content=":white_check_mark: | Correct! Guess you get to live.",
                view=self.view,
            )
        else:
            self.view.value = True
            await interaction.response.edit_message(
                content=":negative_squared_cross_mark: | Wrong answer! Now you go to feed the fishies!",
                view=self.view,
            )


class RiddleView(discord.ui.View):
    def __init__(self, answer, *, timeout=180):
        self.answer = answer.lower()
        super().__init__(timeout=timeout)
        self.add_item(TextInput(style=discord.TextStyle.short, required=True, label="Answer:"))

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(
            content=":negative_squared_cross_mark: | Too slow! Now you go to feed the fishies!",
            view=self,
        )
