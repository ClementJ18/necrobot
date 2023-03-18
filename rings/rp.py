import discord
from discord.ext import commands

from rings.utils.utils import time_converter
from rings.utils.ui import paginate

import datetime


class RP(commands.Cog):
    """Contains commands made specifically for RP purposes."""

    def __init__(self, bot):
        self.bot = bot


    def cog_check(self, ctx):
        if ctx.guild:
            return True

        raise commands.CheckFailure("This command cannot be used in private messages.")

    @commands.command()
    async def activity(self, ctx, *, duration : str = None):
        """Get a list of channels that have had a message in the last amount of time specified.
        The following times can be used: days (d), hours (h), minutes (m), seconds (s).

        {usage}

        __Examples__
        {pre}activity 2d - Get channels that have had a message in the last 2 days
        """
        now = discord.utils.utcnow()
        time = 300

        if duration is not None:
            time = time_converter(duration)

        def is_active(ch):
            if getattr(ch, "last_message_id", None) is None:
                return False

            ch_time = discord.utils.snowflake_time(ch.last_message_id)
            return ch_time > (now - datetime.timedelta(seconds=time))

        def embed_maker(view, entries):
            formatted_channels = '\n'.join([f"{channel.mention} - {(now - discord.utils.snowflake_time(last_message_id)).seconds // 60} minute(s) ago" for channel, last_message_id in entries])

            embed = discord.Embed(
                title=f"Active Channels ({view.page_number}/{view.page_count})",
                description=f"List of channels that have had a message in the last {time//60} minute(s) \n {formatted_channels}",
                colour=self.bot.bot_color,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        channels = [(channel, channel.last_message_id) for channel in [*ctx.guild.channels, *ctx.guild.threads] if is_active(channel) and channel.id != ctx.channel.id]
        channels.sort(key=lambda x: (now - discord.utils.snowflake_time(x[1])).seconds)

        await paginate(ctx, channels, 10, embed_maker)



async def setup(bot):
    await bot.add_cog(RP(bot))
