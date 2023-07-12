import datetime
from typing import Union

import discord
from discord.ext import commands

from rings.utils.ui import paginate
from rings.utils.utils import time_converter


class RP(commands.Cog):
    """Contains commands made specifically for RP purposes."""

    def __init__(self, bot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context):
        if ctx.guild:
            return True

        raise commands.CheckFailure("This command cannot be used in private messages.")

    async def _activity(self, ctx: commands.Context, duration, channels):
        def is_active(ch):
            if getattr(ch, "last_message_id", None) is None:
                return False

            ch_time = discord.utils.snowflake_time(ch.last_message_id)
            return ch_time > (now - datetime.timedelta(seconds=time))

        now = discord.utils.utcnow()
        time = 300
        if duration is not None:
            time = time_converter(duration)

        filtered_channels = [
            channel
            for channel in channels
            if is_active(channel[0]) and channel[0].id != ctx.channel.id
        ]
        filtered_channels.sort(key=lambda x: (now - discord.utils.snowflake_time(x[1])).seconds)

        def embed_maker(view, entries):
            formatted_channels = "\n".join(
                [
                    f"{channel.mention} - {(now - discord.utils.snowflake_time(last_message_id)).seconds // 60} minute(s) ago"
                    for channel, last_message_id in entries
                ]
            )

            embed = discord.Embed(
                title=f"Active Channels ({view.page_number}/{view.page_count})",
                description=f"List of channels that have had a message in the last {time//60} minute(s) \n {formatted_channels}",
                colour=self.bot.bot_color,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        await paginate(ctx, filtered_channels, 10, embed_maker)

    @commands.group(invoke_without_command=True)
    async def activity(self, ctx: commands.Context, *, duration: str = None):
        """Get a list of channels that have had a message in the last amount of time specified.
        The following times can be used: days (d), hours (h), minutes (m), seconds (s).

        {usage}

        __Examples__
        {pre}activity 2d - Get channels that have had a message in the last 2 days
        """
        channels = [
            (channel, channel.last_message_id)
            for channel in [*ctx.guild.text_channels, *ctx.guild.threads]
        ]
        await self._activity(ctx, duration, channels)

    @activity.command(name="ignore")
    async def activity_ignore(
        self,
        ctx: commands.Context,
        ignored: commands.Greedy[
            Union[discord.TextChannel, discord.CategoryChannel, discord.Thread]
        ],
        *,
        duration: str = None,
    ):
        to_ignore = [ctx.channel.id]

        for channel in ignored:
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                to_ignore.append(channel.id)
            else:
                to_ignore.extend([ch.id for ch in channel.channels])

        channels = [
            (channel, channel.last_message_id)
            for channel in [*ctx.guild.text_channels, *ctx.guild.threads]
            if channel.id not in to_ignore
        ]
        await self._activity(ctx, duration, channels)


async def setup(bot):
    await bot.add_cog(RP(bot))
