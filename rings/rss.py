import discord
from discord.ext import commands

from rings.utils.utils import react_menu, BotError, check_channel
from rings.utils.checks import has_perms

import feedparser
import asyncio
import datetime
import re
from bs4 import BeautifulSoup

def convert(time):
    return datetime.datetime.strptime(time[:-3] + time[-2:], '%Y-%m-%dT%H:%M:%S%z')

class RSS(commands.Cog):
    """Cog for keeping up to date with a bunch of different stuff automatically."""

    def __init__(self, bot):
        self.bot = bot
        self.base_youtube = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
        self.task = self.bot.loop.create_task(self.rss_task())
        
    #######################################################################
    ## Cog Functions
    #######################################################################

    def cog_unload(self):
        self.task.cancel()
        
    #######################################################################
    ## Functions
    #######################################################################
    
    async def youtube_sub_task(self):
        feeds = await self.bot.db.query("""
            SELECT youtuber_id, min(last_update), array_agg((channel_id, filter)::channel_filter_hybrid) 
            FROM necrobot.Youtube 
            GROUP BY youtuber_id
        """)
        
        time_limit = await self.bot.db.update_yt_rss()
        
        to_send = []
        
        for feed in feeds:
            async with self.bot.session.get(self.base_youtube.format(feed[0])) as resp:
                parsed_feed = feedparser.parse(await resp.text())["entries"]
                parsed_feed.reverse()
                
                d = {"channels": feed[2], "entries": []}
                for x in parsed_feed:
                    try:
                        if time_limit > convert(x["published"]):
                            d["entries"].append(x)
                    except KeyError:
                        await self.bot.get_bot_channel().send(x["link"])
                        return
                    
                to_send.append({
                    "channels": feed[2], 
                    "entries": [x for x in parsed_feed if time_limit > convert(x["published"]) > feed[1]]
                })

        for feed in to_send:
            for entry in feed["entries"]:
                description = entry["summary"].splitlines()
                embed = discord.Embed(title=entry["title"], description=description[0] if description else "No description", url=entry["link"])
                embed.set_author(name=entry["author_detail"]["name"], url=entry["author_detail"]["href"])
                embed.set_thumbnail(url=entry["media_thumbnail"][0]["url"])
                embed.set_footer(**self.bot.bot_footer)

                for channel_id, title_filter in feed["channels"]:
                    if title_filter in entry["title"].lower():
                        await self.bot.get_channel(channel_id).send(embed=embed)

    async def rss_task(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                await asyncio.sleep(900)
                await self.youtube_sub_task()
            except asyncio.CancelledError:
                return
            except Exception as e:
                self.bot.dispatch("error", e)

    #######################################################################
    ## Commands 
    #######################################################################
    
    @commands.group(invoke_without_command = True, aliases=["yt"])
    @has_perms(3)
    async def youtube(self, ctx, youtube : str = None, channel : discord.TextChannel = None):
        """Add/edit a youtube stream. As long as you provide a channel, the stream will be set to that
        channelYou can simply pass a channel URL for the ID to be retrieved.
        
        {usage}

        __Example__
        `{pre}youtube https://www.youtube.com/channel/UCj4W7A7gHxGDspYBHiw6R #streams` - subscribe to the youtube channel with this id and send all 
        new videos to the #streams
        `{pre}youtube` - list all youtube  channels you are subbed to and which discord channel they are being sent to.
        """
        if youtube is None:
            if channel is not None:
                raise BotError("Please provide a channel to set the youtube stream to")

            feeds = await self.bot.db.get_yt_rss(ctx.guild.id)

            def embed_generator(page, entries):
                to_string = [f"[{result[5]}](https://www.youtube.com/channel/{result[2]}): {ctx.guild.get_channel(result[1]).mention} - `{result[4] if result[4] != '' else 'None'}`" for result in entries]
                embed = discord.Embed(title=f"Subscriptions ({page[0]}/{page[1]})", description = "\n".join(to_string))
                embed.set_footer(**self.bot.bot_footer)

                return embed

            return await react_menu(ctx, feeds, 15, embed_generator)
        
        
        check_channel(channel)
        try:        
            async with self.bot.session.get(youtube) as resp:
                if resp.status != 200:
                    raise BotError("This channel does not exist, double check the youtuber id.")
                
                try:
                    youtuber_id = re.findall(r'"external(?:Channel)?Id":"([^,.]*)"', await resp.text())[0]
                except IndexError:
                    raise BotError("Could not find the user ID")            
        except:
            
            raise BotError("Not a valid youtube URL")
            
        soup = BeautifulSoup(await resp.text(), "html.parser")
        name = soup.find("title").string.replace(" - YouTube", "")      
        
        await self.bot.db.upsert_yt_rss(ctx.guild.id, channel.id, youtuber_id, name)
        await ctx.send(f":white_check_mark: | New videos from this channel will now be posted in {channel.mention}.")

    @youtube.command(name="delete")
    @has_perms(3)
    async def youtube_delete(self, ctx, *, youtuber_name):
        """This subcommand allows you to unsubscribe from a youtube channel based on the name
        
        {usage}
        
        __Example__
        `{pre}youtube delete Jojo` - remove the channel called Jojo
        """
        deleted = await self.bot.db.query(
            "DELETE FROM necrobot.Youtube WHERE guild_id = $1 AND LOWER(youtuber_name) = LOWER($2) RETURNING youtuber_name",
            ctx.guild.id, youtuber_name    
        )
        
        if not deleted:
            raise BotError("No channel with that name")
            
        await ctx.send(f":white_check_mark: | Deleted channel **{'**, **'.join([x[0] for x in deleted])}**")


    @youtube.command(name="filters")
    @has_perms(3)
    async def youtube_filters(self, ctx, youtuber_name : str, *, filters : str = ""):
        """This subcommand allows you to set a filter so that only videos which posses these keywords will be posted.
        The filter itself is very rudimentary but will work so that any video that has exactly these words (in
        any case) in that order in the title will be posted. You can clear filters by calling this command with just
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
            await ctx.send(":white_check_mark: | Filters have been disabled for this channel")
        else:
            await ctx.send(f":white_check_mark: | Only videos with the words: **{filters}** will be posted for this yt channel")

def setup(bot):
    bot.add_cog(RSS(bot))
