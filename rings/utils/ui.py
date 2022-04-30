import discord

class Confirm(discord.ui.View):
    def __init__(self, confirm_msg="Confirmed", cancel_msg="Cancelled"):
        super().__init__()
        self.value = None
        self.confirm_msg = confirm_msg
        self.cancel_msg = cancel_msg

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content=self.confirm_msg, view=self)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()
        self.clear_items()
        await interaction.response.edit_message(content=self.cancel_msg, view=self)
