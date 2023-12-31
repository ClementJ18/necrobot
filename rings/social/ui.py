import discord

from rings.utils.ui import BaseView
from rings.utils.utils import NEGATIVE_CHECK, POSITIVE_CHECK


class TextInput(discord.ui.TextInput):
    async def callback(self, interaction):
        self.view.stop()
        self.view.clear_items()

        if self.value.lower() == self.view.answer:
            self.view.value = True
            await interaction.response.edit_message(
                content=f"{POSITIVE_CHECK} | Correct! Guess you get to live.",
                view=self.view,
            )
        else:
            self.view.value = True
            await interaction.response.edit_message(
                content=f"{NEGATIVE_CHECK} | Wrong answer! Now you go to feed the fishies!",
                view=self.view,
            )


class RiddleView(BaseView):
    def __init__(self, answer, *, timeout=180):
        self.answer = answer.lower()
        super().__init__(timeout=timeout)
        self.add_item(TextInput(style=discord.TextStyle.short, required=True, label="Answer:"))
        self.message: discord.Message = None

    async def on_timeout(self):
        self.stop()
        self.clear_items()
        await self.message.edit(
            content=f"{NEGATIVE_CHECK} | Too slow! Now you go to feed the fishies!",
            view=self,
        )
