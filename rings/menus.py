from __future__ import annotations
import io

import typing
import discord

from PIL import Image

from rings.utils.utils import NEGATIVE_CHECK, POSITIVE_CHECK

if typing.TYPE_CHECKING:
    from bot import NecroBot


@discord.app_commands.context_menu(name="Send to starboard")
@discord.app_commands.default_permissions(administrator=True)
@discord.app_commands.guild_only()
async def starboard_force(interaction: discord.Interaction[NecroBot], message: discord.Message):
    if not interaction.client.guild_data[interaction.guild.id]["starboard-channel"]:
        return await interaction.response.send_message(
            f"{NEGATIVE_CHECK} | Please set a starboard first", ephemeral=True
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

    await interaction.followup.send(f"{POSITIVE_CHECK} | Message force starred", ephemeral=True)


@discord.app_commands.context_menu(name="Delete bot message")
async def delete_bot_dm(interaction: discord.Interaction[NecroBot], message: discord.Message):
    # remove this after discord.app_commands.dm_only has been implemented
    if interaction.guild is not None:
        return await interaction.response.send_message(
            f"{NEGATIVE_CHECK} | This action can only be used in DMs", ephemeral=True
        )

    if not message.author.bot:
        return await interaction.response.send_message(
            f"{NEGATIVE_CHECK} | This action can only be used on a bot message", ephemeral=True
        )

    await message.delete()
    await interaction.response.send_message(f"{POSITIVE_CHECK} | Message deleted", ephemeral=True)


@discord.app_commands.context_menu(name="Convert .bmp attachment")
async def convert_bmp(interaction: discord.Interaction[NecroBot], message: discord.Message):
    if not message.attachments:
        return await interaction.response.send_message(
            f"{NEGATIVE_CHECK} | This message has no attachements", ephemeral=True
        )

    to_convert = [img for img in message.attachments if img.filename.endswith(".bmp")]

    if not to_convert:
        return await interaction.response.send_message(
            f"{NEGATIVE_CHECK} | This message has no `.bmp` attachements", ephemeral=True
        )

    await interaction.response.defer()
    converted = []
    for index, img in enumerate(to_convert):
        f = io.BytesIO()
        await img.save(f)

        with Image.open(f) as im:
            output_buffer = io.BytesIO()
            im.save(output_buffer, "png")
            output_buffer.seek(0)
            converted.append(discord.File(filename=f"converted{index}.png", fp=output_buffer))

    await interaction.followup.send(
        f"{POSITIVE_CHECK} | {interaction.user.mention}, I converted the images like you asked",
        files=converted,
    )


async def setup(bot: NecroBot):
    menus = [
        starboard_force,
        delete_bot_dm,
        convert_bmp,
    ]

    for menu in menus:
        bot.tree.add_command(menu)
