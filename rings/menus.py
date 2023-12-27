from __future__ import annotations

import typing
import discord

if typing.TYPE_CHECKING:
    from bot import NecroBot


@discord.app_commands.context_menu(name="Send to starboard")
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.guild_only()
async def starboard_force(interaction: discord.Interaction[NecroBot], message: discord.Message):
    if not interaction.client.guild_data[interaction.guild.id]["starboard-channel"]:
        return await interaction.response.send_message(
            ":negative_squared_cross_mark: | Please set a starboard first", ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)
    await interaction.client.meta.star_message(message)
    automod = interaction.guild.get_channel(interaction.client.guild_data[interaction.guild.id]["automod"])
    if automod is not None:
        embed = discord.Embed(
            title="Message Force Starred",
            description=f"{interaction.user.mention} force starred a message",
            colour=interaction.client.bot_color,
        )
        embed.add_field(name="Link", value=message.jump_url)
        embed.set_footer(**interaction.client.bot_footer)
        await automod.send(embed=embed)

    await interaction.followup.send(":white_check_mark: | Message force starred", ephemeral=True)


async def setup(bot: NecroBot):
    bot.tree.add_command(starboard_force)
