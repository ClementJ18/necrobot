from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Dict, List, Tuple, Union

import discord
from discord.ext import commands

from rings.db import DatabaseError
from rings.utils.ui import Paginator
from rings.utils.utils import time_converter

if TYPE_CHECKING:
    from bot import NecroBot


class RP(commands.Cog):
    """Contains commands made specifically for RP purposes."""

    def __init__(self, bot: NecroBot):
        self.bot = bot

    def cog_check(self, ctx: commands.Context[NecroBot]):
        if ctx.guild:
            return True

        raise commands.CheckFailure("This command cannot be used in private messages.")

    async def _activity(
        self,
        ctx: commands.Context[NecroBot],
        duration: int,
        channels: List[Tuple[discord.TextChannel, int]],
    ):
        def is_active(ch: discord.TextChannel):
            if getattr(ch, "last_message_id", None) is None:
                return False

            ch_time = discord.utils.snowflake_time(ch.last_message_id)
            return ch_time > (now - datetime.timedelta(seconds=time))

        now = datetime.datetime.now(datetime.timezone.utc)
        time = 300
        if duration is not None:
            time = time_converter(duration)

        filtered_channels = [
            channel for channel in channels if is_active(channel[0]) and channel[0].id != ctx.channel.id
        ]
        filtered_channels.sort(key=lambda x: (now - discord.utils.snowflake_time(x[1])).seconds)

        def embed_maker(view: Paginator, entries: List[Tuple[discord.TextChannel, datetime.datetime]]):
            formatted_channels = "\n".join(
                [
                    f"{channel.mention} - {(now - discord.utils.snowflake_time(last_message_id)).seconds // 60} minute(s) ago"
                    for channel, last_message_id in entries
                ]
            )

            embed = discord.Embed(
                title=f"Active Channels ({view.page_string})",
                description=f"List of channels that have had a message in the last {time//60} minute(s) \n {formatted_channels}",
                colour=self.bot.bot_color,
            )

            embed.set_footer(**self.bot.bot_footer)

            return embed

        await Paginator(10, filtered_channels, ctx.author, embed_maker=embed_maker).start(ctx)

    @commands.group(invoke_without_command=True)
    async def activity(self, ctx: commands.Context[NecroBot], *, duration: str = None):
        """Get a list of channels that have had a message in the last amount of time specified. \
        The following times can be used: days (d), hours (h), minutes (m), seconds (s).

        {usage}

        __Examples__
        `{pre}activity 2d` - Get channels that have had a message in the last 2 days
        """
        combined: List[Union[discord.TextChannel, discord.Thread]] = [
            *ctx.guild.text_channels,
            *ctx.guild.threads,
        ]
        channels = [(channel, channel.last_message_id) for channel in combined]
        await self._activity(ctx, duration, channels)

    @activity.command(name="ignore")
    async def activity_ignore(
        self,
        ctx: commands.Context[NecroBot],
        ignored: commands.Greedy[Union[discord.TextChannel, discord.CategoryChannel, discord.Thread]],
        *,
        duration: str = None,
    ):
        """Get a list of channels that have a had a message in the last amount of time specific \
        but you can also ignore certain channels you don't have to be taken into consideration.
        
        {usage}
        
        __Examples__
        `{pre}activity ignore #general #bot 2d` - Get channels that have had a message in the last two days not  \
        including the bot and general channels.
        """
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

    @commands.group(invoke_without_command=True)
    async def subscribe(
        self, ctx: commands.Context[NecroBot], channel: Union[discord.TextChannel, discord.Thread]
    ):
        """Subscribe to a channel. The bot will DM you if a new message is posted in the channel. This
        has an internal cooldown to avoid spam.

        {usage}

        __Examples__
        `{pre}subscribe #news` - subscribe to the news channel
        """
        if not channel.permissions_for(ctx.author).read_messages:
            return await ctx.send(
                ":negative_squared_cross_mark: | You do not have permission to read this channel."
            )

        if not channel.permissions_for(ctx.guild.me).read_messages:
            return await ctx.send(
                ":negative_squared_cross_mark: | I do not have permission to read this channel."
            )

        try:
            await self.bot.db.query(
                "INSERT INTO necrobot.ChannelSubscriptions(user_id, channel_id) VALUES($1, $2)",
                ctx.author.id,
                channel.id,
            )
            await ctx.send(
                f":white_check_mark: | You are now subscribed to {channel.mention}. Make sure your DMs are open!"
            )
        except DatabaseError:
            await ctx.send(
                ":negative_squared_cross_mark: | Could not subscribe. You might already subscribed."
            )

    @subscribe.command(name="list")
    async def subscribe_list(self, ctx: commands.Context[NecroBot]):
        """List all your subscriptions.

        {usage}

        __Examples__
        `{pre}subscribe list` - list all your subscriptions"""
        subscriptions = await self.bot.db.query(
            "SELECT channel_id from necrobot.ChannelSubscriptions WHERE user_id = $1", ctx.author.id
        )

        def embed_maker(view: Paginator, entries: List[int]):
            channels = [
                f"- {self.bot.get_channel(channel['channel_id']).mention}"
                for channel in entries
                if self.bot.get_channel(channel["channel_id"]) is not None
            ]
            e = discord.Embed(
                title="Subscriptions", description="\n".join(channels), color=self.bot.bot_color
            )
            e.set_footer(**self.bot.bot_footer)

            return e

        await Paginator(15, subscriptions, ctx.author, embed_maker=embed_maker).start(ctx)

    @commands.command()
    async def unsubscribe(
        self, ctx: commands.Context[NecroBot], channel: Union[discord.TextChannel, discord.Thread]
    ):
        """Unsubscribe from a channel to stop the notifications.

        {usage}

        __Examples__
        `{pre}unsubscribe #news` - unsubscribe from #news"""

        is_deleted = await self.bot.db.query(
            "DELETE FROM necrobot.ChannelSubscriptions WHERE user_id = $1 AND channel_id = $2 RETURNING channel_id",
            ctx.author.id,
            channel.id,
            fetchval=True,
        )

        if is_deleted:
            await ctx.send(":white_check_mark: | Subscription cancelled.")
        else:
            await ctx.send(":negative_squared_cross_mark: | Could not find this subscription.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        subscribers = await self.bot.db.query(
            "SELECT user_id FROM necrobot.ChannelSubscriptions WHERE channel_id = $1 AND last_update < NOW() - INTERVAL '5 minutes' AND user_id != $2",
            message.channel.id,
            message.author.id,
        )

        if not subscribers:
            return

        await self.bot.db.query(
            "UPDATE necrobot.ChannelSubscriptions SET last_update = NOW() WHERE channel_id = $1 AND user_id = ANY($2)",
            message.channel.id,
            [subscriber["user_id"] for subscriber in subscribers],
        )

        for subscriber in subscribers:
            try:
                member = message.channel.guild.get_member(subscriber["user_id"])
                if member is not None and message.channel.permissions_for(member).read_messages:
                    await member.send(
                        f"A message was sent to one of your subscribed channels! See here: {message.jump_url}"
                    )
            except discord.Forbidden:
                pass


async def setup(bot: NecroBot):
    await bot.add_cog(RP(bot))
