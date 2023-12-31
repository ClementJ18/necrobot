from __future__ import annotations

import asyncio
import datetime
import random
import re
import time
from collections import defaultdict
from time import mktime
from typing import TYPE_CHECKING, Annotated, Dict, List

import discord
import feedparser
from bs4 import BeautifulSoup
from discord.ext import commands

from rings.utils.checks import has_perms
from rings.utils.config import twitch_id
from rings.utils.converters import WritableChannelConverter
from rings.utils.ui import Paginator
from rings.utils.utils import POSITIVE_CHECK, BotError

if TYPE_CHECKING:
    from bot import NecroBot


def convert(t):
    return datetime.datetime.strptime(t[:-3] + t[-2:], "%Y-%m-%dT%H:%M:%S%z")


class RSS(commands.Cog):
    """Cog for keeping up to date with a bunch of different stuff automatically."""

    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.base_youtube = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
        self.task = None

    #######################################################################
    ## Cog Functions
    #######################################################################

    async def cog_unload(self):
        self.task.cancel()

    async def cog_load(self):
        self.task = self.bot.loop.create_task(self.rss_task())

    #######################################################################
    ## Functions
    #######################################################################

    async def youtube_sub_task(self):
        feeds = await self.bot.db.query(
            """
            SELECT youtuber_id, min(last_update), array_agg((channel_id, filter)::channel_filter_hybrid) 
            FROM necrobot.Youtube 
            GROUP BY youtuber_id
        """
        )

        to_send = []
        for feed in feeds:
            async with self.bot.session.get(self.base_youtube.format(feed[0])) as resp:
                parsed_feed = feedparser.parse(await resp.text())["entries"]

            if not parsed_feed:
                continue

            date = convert(parsed_feed[0]["published"])
            if date <= feed[1]:
                continue

            parsed_feed.reverse()

            d = {"channels": feed[2], "entries": []}
            for entry in parsed_feed:
                published = convert(entry["published"])
                if published > feed[1]:
                    d["entries"].append(entry)

            to_send.append(d)

            await self.bot.db.query(
                "UPDATE necrobot.Youtube SET last_update=$1 WHERE youtuber_id=$2",
                date,
                feed[0],
            )

        for feed in to_send:
            for entry in feed["entries"]:
                description = entry["summary"].splitlines()
                embed = discord.Embed(
                    title=entry["title"],
                    description=description[0] if description else "No description",
                    url=entry["link"],
                )
                embed.set_author(
                    name=entry["author_detail"]["name"],
                    url=entry["author_detail"]["href"],
                )
                embed.set_thumbnail(url=entry["media_thumbnail"][0]["url"])
                embed.set_footer(**self.bot.bot_footer)

                for channel_id, title_filter in feed["channels"]:
                    if title_filter in entry["title"].lower():
                        try:
                            await self.bot.get_channel(channel_id).send(embed=embed)
                        except discord.Forbidden:
                            pass

    async def twitch_sub_task(self):
        entries = await self.bot.db.query("SELECT * FROM necrobot.Twitch")
        if not entries:
            return

        last_time = min([x["last_update"] for x in entries])

        feeds = defaultdict(list)
        for entry in entries:
            feeds[entry["twitch_id"]].append((entry["channel_id"], entry["filter"]))

        streams = await self.get_twitch_streams(list(feeds.keys()))
        time_limit = await self.bot.db.update_tw_rss()

        for stream in streams:
            if (
                datetime.datetime.strptime(stream["started_at"].replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                <= last_time
            ):
                continue

            embed = discord.Embed(
                title="Streamer Live",
                description=f"**{stream['user_name']}** has started streaming. Join here: [{stream['title'] if stream['title'] else 'Link'}](https://www.twitch.tv/{stream['user_name']}).",
            )
            embed.set_thumbnail(url=stream["thumbnail_url"].format(width=1280, height=720))
            embed.set_footer(**self.bot.bot_footer)

            for channel, title_filter in feeds[str(stream["user_id"])]:
                if title_filter in stream["title"].lower():
                    try:
                        await self.bot.get_channel(channel).send(embed=embed)
                    except discord.Forbidden:
                        pass

    async def rss_task(self):
        await self.bot.wait_until_loaded()
        while not self.bot.is_closed():
            try:
                await self.youtube_sub_task()
                await self.twitch_sub_task()
            except asyncio.CancelledError:
                return
            except Exception as e:
                self.bot.dispatch("error", e)
            finally:
                await asyncio.sleep(600)

    #######################################################################
    ## Commands
    #######################################################################

    @commands.group(invoke_without_command=True, aliases=["yt"])
    @has_perms(3)
    async def youtube(
        self,
        ctx: commands.Context[NecroBot],
        youtube: str = None,
        *,
        channel: Annotated[discord.TextChannel, WritableChannelConverter] = None,
    ):
        """Add/edit a youtube stream. As long as you provide a channel, the stream will be set to that \
        channelYou can simply pass a channel URL for the ID to be retrieved.

        {usage}

        __Example__
        `{pre}youtube https://www.youtube.com/channel/UCj4W7A7gHxGDspYBHiw6R #streams` - subscribe to the youtube channel with this id and send all
        new videos to the #streams
        `{pre}youtube` - list all youtube  channels you are subbed to and which discord channel they are being sent to.
        """
        if youtube is None:
            feeds = await self.bot.db.get_yt_rss(ctx.guild.id)

            def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
                to_string = [
                    f"[{result[5]}](https://www.youtube.com/channel/{result[2]}): {ctx.guild.get_channel(result[1]).mention} - `{result[4] if result[4] != '' else 'None'}`"
                    for result in entries
                ]
                embed = discord.Embed(
                    title=f"Subscriptions ({view.page_string})",
                    description="\n".join(to_string),
                )
                embed.set_footer(**self.bot.bot_footer)

                return embed

            return await Paginator(15, feeds, ctx.author, embed_maker=embed_maker).start(ctx)

        try:
            async with self.bot.session.get(
                youtube,
                cookies={
                    "SOCS": "CAISNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjMwODI5LjA3X3AxGgJlbiACGgYIgLC_pwY"
                },
            ) as resp:
                if resp.status != 200:
                    raise BotError("This channel does not exist, double check the youtuber id.")

                try:
                    text = await resp.text()
                    youtuber_id = re.findall(r'"external(?:Channel)?Id":"([^,.]*)"', text)[0]
                except IndexError as e:
                    raise BotError("Could not find the user ID") from e
        except Exception as e:
            raise BotError(f"Not a valid youtube URL: {e}") from e

        soup = BeautifulSoup(await resp.text(), "html.parser")
        name = soup.find("title").string.replace(" - YouTube", "")

        if channel is not None:
            await self.bot.db.upsert_yt_rss(ctx.guild.id, channel.id, youtuber_id, name)
            await ctx.send(
                f"{POSITIVE_CHECK} | New videos from **{name}** will now be posted in {channel.mention}."
            )
        else:
            await self.bot.db.delete_yt_rss_channel(ctx.guild.id, youtuber_name=name)
            await ctx.send(f"{POSITIVE_CHECK} | Upload notifications for **{name}** disabled.")

    @youtube.command(name="delete")
    @has_perms(3)
    async def youtube_delete(self, ctx: commands.Context[NecroBot], *, youtuber_name):
        """This subcommand allows you to unsubscribe from a youtube channel based on the name

        {usage}

        __Example__
        `{pre}youtube delete Jojo` - remove the channel called Jojo
        """
        deleted = await self.bot.db.query(
            "DELETE FROM necrobot.Youtube WHERE guild_id = $1 AND LOWER(youtuber_name) = LOWER($2) RETURNING youtuber_name",
            ctx.guild.id,
            youtuber_name,
        )

        if not deleted:
            raise BotError("No channel with that name")

        await ctx.send(f"{POSITIVE_CHECK} | Deleted channel **{'**, **'.join([x[0] for x in deleted])}**")

    @youtube.command(name="filters")
    @has_perms(3)
    async def youtube_filters(
        self, ctx: commands.Context[NecroBot], youtuber_name: str, *, filters: str = ""
    ):
        """This subcommand allows you to set a filter so that only videos which posses these keywords will be posted. \
        The filter itself is very rudimentary but will work so that any video that has exactly these words (in \
        any case) in that order in the title will be posted. You can clear filters by calling this command with just \
        a youtuber id. Filters are limited to 200 characters

        {usage}

        __Examples__
        `{pre}youtube filters Jojo edain` - only post videos containing the word `edain`in their title
        `{pre}youtube filters Jojo - clear all filters for that channel, posting every video
        """
        updated = await self.bot.db.update_yt_filter(ctx.guild.id, youtuber_name, filters.lower())
        if not updated:
            raise BotError("No channel with that name")

        if filters == "":
            await ctx.send(f"{POSITIVE_CHECK} | Filters have been disabled for {youtuber_name}")
        else:
            await ctx.send(
                f"{POSITIVE_CHECK} | Only videos with the words **{filters}** will be posted for **{youtuber_name}**"
            )

    async def twitch_request(self, route, payload):
        if self.bot.twitch_token.get("expires") is None:
            await self.bot.meta.refresh_token()

        if time.time() > self.bot.twitch_token["expires"]:
            await self.bot.meta.refresh_token()

        headers = {
            "Authorization": f'Bearer {self.bot.twitch_token["token"]}',
            "Client-Id": twitch_id,
        }

        async with self.bot.session.get(
            f"https://api.twitch.tv/helix/{route}", headers=headers, params=payload
        ) as resp:
            return await resp.json()

    async def get_twitch_user(self, user_name):
        resp = await self.twitch_request("users", {"login": user_name})
        data = resp["data"]

        if not data:
            raise BotError(f"No twitch user found with name {user_name}")

        return data[0]

    async def get_twitch_streams(self, user_ids):
        n = 100
        chunks = [user_ids[i : i + n] for i in range(0, len(user_ids), n)]

        streams = []
        for chunk in chunks:
            payload = [("first", n)] + [("user_id", x) for x in chunk]
            resp = await self.twitch_request("streams", payload)
            streams.extend(resp["data"])

        return streams

    @commands.group(invoke_without_command=True)
    @has_perms(3)
    async def twitch(
        self,
        ctx: commands.Context[NecroBot],
        twitch: str = None,
        *,
        channel: Annotated[discord.TextChannel, WritableChannelConverter] = None,
    ):
        """Add/edit twitch streams. Simply provide a channel name or url to get started

        {usage}

        __Examples__
        `{pre}twitch scarra #streams` - subscribe to scarra, you will notified whenever they go live
        `{pre}twitch https://www.twitch.tv/scarra #streams` - subscribe to scarra, you will notified whenever they go live
        """
        if twitch is None:
            feeds = await self.bot.db.get_tw_rss(ctx.guild.id)

            def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
                to_string = [
                    f"[{result[5]}](https://www.twitch.tv/{result['twitch_name']}): {ctx.guild.get_channel(result[1]).mention} - `{result[4] if result[4] != '' else 'None'}`"
                    for result in entries
                ]
                embed = discord.Embed(
                    title=f"Subscriptions ({view.page_string})",
                    description="\n".join(to_string),
                )
                embed.set_footer(**self.bot.bot_footer)

                return embed

            return await Paginator(15, feeds, ctx.author, embed_maker=embed_maker).start(ctx)

        if channel is not None:
            twitch = re.sub(r"https?:\/\/(?:(?:www|go|m)\.)?twitch\.tv\/", "", twitch)
            user = await self.get_twitch_user(twitch)

            await self.bot.db.upsert_tw_rss(ctx.guild.id, channel.id, user["id"], user["login"])
            await ctx.send(
                f"{POSITIVE_CHECK} | Live streams from **{user['display_name']}** will now be posted in {channel.mention}."
            )
        else:
            await self.bot.db.delete_tw_rss_channel(ctx.guild.id, twitch_name=twitch)
            await ctx.send(f"{POSITIVE_CHECK} | Live stream notifications for **{twitch}** disabled.")

    @twitch.command(name="delete")
    @has_perms(3)
    async def twitch_delete(self, ctx: commands.Context[NecroBot], *, twitch_name):
        """This subcommand allows you to unsubscribe from a twitch channel based on the name

        {usage}

        __Example__
        `{pre}twitch delete scarra` - remove the channel called scarra
        """
        deleted = await self.bot.db.query(
            "DELETE FROM necrobot.Twitch WHERE guild_id = $1 AND LOWER(twitch_name) = LOWER($2) RETURNING twitch_name",
            ctx.guild.id,
            twitch_name,
        )

        if not deleted:
            raise BotError("No channel with that name")

        await ctx.send(f"{POSITIVE_CHECK} | Deleted channel **{'**, **'.join([x[0] for x in deleted])}**")

    @twitch.command(name="filters")
    @has_perms(3)
    async def twitch_filters(self, ctx: commands.Context[NecroBot], twitch_name: str, *, filters: str = ""):
        """This subcommand allows you to set a filter so that only videos which posses these keywords will be posted. \
        The filter itself is very rudimentary but will work so that any video that has exactly these words (in \
        any case) in that order in the title will be posted. You can clear filters by calling this command with just \
        a youtuber id. Filters are limited to 200 characters \

        {usage}

        __Examples__
        `{pre}youtube filters scarra edain` - only post videos containing the word `edain`in their title
        `{pre}youtube filters scarra - clear all filters for that channel, posting every video
        """
        updated = await self.bot.db.update_tw_filter(ctx.guild.id, twitch_name, filters.lower())
        if not updated:
            raise BotError("No channel with that name")

        if filters == "":
            await ctx.send(f"{POSITIVE_CHECK} | Filters have been disabled for {twitch_name}")
        else:
            await ctx.send(
                f"{POSITIVE_CHECK} | Only streams with the words **{filters}** will be posted for **{twitch_name}**"
            )


async def setup(bot: NecroBot):
    await bot.add_cog(RSS(bot))
