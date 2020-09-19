import discord
from discord.ext import commands

from rings.db import SyncDatabase
from rings.utils.config import token
from rings.utils.utils import get_pre
from rings.utils.help import NecrobotHelp

import json
import time
import asyncio
import logging
import datetime
import traceback

logging.basicConfig(filename='discord.log',level=logging.ERROR)
# logging.basicConfig(level=logging.CRITICAL)

class NecroBot(commands.Bot):
    def __init__(self):
        super().__init__(
            max_messages=50000,
            fetch_offline_members=True,
            activity=discord.Game("n!help for help"),
            case_insensitive=True,
            description="A bot for managing and enhancing servers",
            command_prefix=get_pre,
            help_command=NecrobotHelp(),
            allowed_mentions=discord.AllowedMentions(everyone=False)     
        )
        
        self.uptime_start = time.time()
        self.counter = datetime.datetime.now().hour
        
        self.version = 3.1
        self.ready = False
        self.prefixes = ["n!", "N!", "n@", "N@"]
        self.admin_prefixes = ["n@", "N@"]
        self.new_commands = ["mu", "maintenance"]
        self.statuses = ["n!help for help", "currently in {guild} guilds", "with {members} members", "n!report for bug/suggestions", "recently upgraded to v3!"]
        self.perms_name = ["User", "Helper", "Moderator", "Semi-Admin", "Admin", "Server Owner", "NecroBot Admin", "Bot Smiths"]
        
        
        self.bot_channel = 318465643420712962
        self.error_channel = 415169176693506048
        self.session = None
        self.pool = None
        self.maintenance = False
        
        sync_db = SyncDatabase()
        self.guild_data = sync_db.load_guilds()
        self.polls = sync_db.load_polls()

        self.cat_cache = []
        self.events = {}
        self.ignored_messages = []
        self.starred = []
        self.potential_stars = {}
        self.reminders = {}
        self.pending_posts = {}
        self.denied_posts = []
        self.queued_posts = asyncio.Queue()
        
        with open("rings/utils/data/settings.json", "rb") as infile:
            self.settings = json.load(infile)
        
        @self.check
        def disabled_check(ctx):
            """This is the backbone of the disable command. If the command name is in disabled then
            we check to make sure that it's not an admin trying to invoke it with an admin prefix """
            if isinstance(ctx.message.channel, discord.DMChannel):
                return True

            disabled = self.guild_data[ctx.message.guild.id]["disabled"]

            if ctx.command.name in disabled and ctx.prefix not in self.admin_prefixes:
                raise commands.CheckFailure("This command has been disabled")

            return True
                
        self.add_check(disabled_check)
        
        @self.check
        async def allowed_summon(ctx):
            if isinstance(ctx.message.channel, discord.DMChannel):
                return True
                
            roles = [role.id for role in ctx.author.roles]
            user_id = ctx.author.id
            guild_id = ctx.guild.id

            if ctx.prefix in self.admin_prefixes:
                permission_level = await self.db.get_permission(user_id, guild_id)
                if permission_level > 0:
                    return True
                raise commands.CheckFailure("You are not allowed to use admin prefixes")

            if user_id in self.guild_data[guild_id]["ignore-command"]:
                raise commands.CheckFailure("You are being ignored by the bot")

            if ctx.channel.id in self.guild_data[guild_id]["ignore-command"]:
                raise commands.CheckFailure("Commands not allowed in this channel.")

            if any(x in roles for x in self.guild_data[guild_id]["ignore-command"]):
                roles = [f"**{x.name}**" for x in ctx.author.roles if x.id in self.guild_data[guild_id]["ignore-command"]]
                raise commands.CheckFailure(f"Roles {', '.join(roles)} aren't allowed to use commands.")

            return True

        self.add_check(allowed_summon)
        
    def clear(self):
        self._closed = False
        self._ready.clear()
        # self._connection.clear()
        self.http.recreate()

    def get_bot_channel(self):
        return self.get_channel(self.bot_channel)
        
    def get_error_channel(self):
        return self.get_channel(self.error_channel)
        
    def blacklist_check(self, object_id):
        return object_id in self.settings["blacklist"]
        
    @property
    def meta(self):
        return self.get_cog("Meta")
        
    @property
    def db(self):
        return self.get_cog("Database")
        
    async def invoke(self, ctx):
        if self.maintenance and ctx.command is not None:
            return await ctx.channel.send(":negative_squared_cross_mark: | Maintenance mode engaged, the bot is not currently accepting commands")
        
        await super().invoke(ctx)
        
    async def wait_for(self, event, *, check=None, timeout=None, handler=None, propagate=True):
        """
        handler : callable
            Function that performs clean up in the case that the timeout is reached
        propagate : bool
            Dictate what happens if an error happens
                True - Error is raised
                None - Nothing
                False - Error is raised but silenced
        """
        try:
            return await super().wait_for(event, check=check, timeout=timeout)
        except asyncio.TimeoutError as e:
            if callable(handler):
                await handler()
            
            if propagate is not None:
                if propagate:
                    e.timer = timeout
                
                raise e

    async def on_ready(self):
        """If this is the first time the boot is booting then we load the cache and set the
        ready variable to True to signify the bot is ready. Else we assume that it means the
        bot had a hiccup and is resuming."""
        if not self.ready:
            await self.meta.load_cache()
            self.ready = True
            print(self.guild_data)
            print('------')
            print(f"Logged in as {self.user}")
            
    # async def on_resumed(self):
    #     """Bot is resuming, log it and move on"""
    #     await self.get_bot_channel().send(f"**Bot Resumed**\nMessage Cache: {len(self._connection._messages)}")
        
    async def on_error(self, event, *args, **kwargs): 
        """Something has gone wrong so we just try to send a helpful traceback to the channel. If
        the traceback is too big we just send the method/event that errored out and hope that
        the error is obvious."""
        channel = self.get_error_channel()
        
        if isinstance(event, Exception):
            error_traceback = " ".join(traceback.format_exception(type(event), event, event.__traceback__, chain=True))
        else:
            error_traceback = traceback.format_exc()

        embed = discord.Embed(title="Error", description=f"```py\n{error_traceback}\n```", colour=discord.Colour(0x277b0))
        embed.add_field(name='Event', value=event, inline=False)
        embed.set_footer(text="Generated by NecroBot", icon_url=self.user.avatar_url_as(format="png", size=128))
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            logging.error(error_traceback)
            
    async def on_message(self, message):
        if self.blacklist_check(message.author.id):
            return
            
        if message.type != discord.MessageType.default or message.author.bot:
            return
            
        self.dispatch("message_approved", message)
        await self.process_commands(message)

                
extensions = [
    'db',
    'meta',
    'wiki',
    'events',
    'admin',
    'support',
    'decisions',
    'misc',
    'words',
    'utilities',
    'social',
    'modding',
    'rss',
    'tags',
    'server',
    'moderation',
    'profile',
    'economy',
    'special'
]

if __name__ == '__main__':
    bot = NecroBot()
    
    @bot.command(hidden=True)
    @commands.is_owner()
    async def load(ctx, extension_name : str):
        """Loads the extension name if in NecroBot's list of rings.
        
        {usage}"""
        try:
            ctx.bot.load_extension(f"rings.{extension_name}")
            await ctx.send(f"{extension_name} loaded.")
        except commands.ExtensionFailed as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")
        except commands.ExtensionNotFound:
            pass

    @bot.command(hidden=True)
    @commands.is_owner()
    async def unload(ctx, extension_name : str):
        """Unloads the extension name if in NecroBot's list of rings.
         
        {usage}"""
        try:
            ctx.bot.unload_extension(f"rings.{extension_name}")
            await ctx.send(f"{extension_name} unloaded.")
        except commands.ExtensionFailed as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")
        except commands.ExtensionNotLoaded:
            pass

    @bot.command(hidden=True)
    @commands.is_owner()
    async def reload(ctx, extension_name : str):
        """Unload and loads the extension name if in NecroBot's list of rings.
         
        {usage}"""
        try:
            ctx.bot.unload_extension(f"rings.{extension_name}")
        except commands.ExtensionFailed as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")
        except commands.ExtensionNotLoaded:
            pass
            
        try:
            ctx.bot.load_extension(f"rings.{extension_name}")
            await ctx.send(f"{extension_name} reloaded.")
        except commands.ExtensionFailed as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")
        except commands.ExtensionNotFound:
            pass

    @bot.command(hidden=True)
    @commands.is_owner()
    async def off(ctx):
        """Saves all the data and terminate the bot. (Permission level required: 7+ (The Bot Smith))
         
        {usage}"""
        msg = await ctx.send("Shut down?")
        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        def check(reaction, user):
            return user.id == 241942232867799040 and str(reaction.emoji) in ["\N{WHITE HEAVY CHECK MARK}", "\N{NEGATIVE SQUARED CROSS MARK}"] and msg.id == reaction.message.id
        
        reaction, _ = await ctx.bot.wait_for(
            "reaction_add", 
            check=check, 
            timeout=300, 
            handler=msg.clear_reactions,
            propagate=False
        )

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            await msg.delete()
        elif reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
            await msg.delete()
            await ctx.bot.change_presence(activity=discord.Game(name="Bot shutting down...", type=0))
            
            with open("rings/utils/data/settings.json", "w") as file:
                json.dump(ctx.bot.settings, file)
            
            await ctx.bot.session.close()
            await ctx.bot.pool.close()
            ctx.bot.meta.hourly_task.cancel()
            for reminder in ctx.bot.reminders.values():
                reminder.cancel()
            
            await ctx.bot.get_bot_channel().send("**Bot Offline**")
            await ctx.bot.logout()

    for extension in extensions:
        bot.load_extension(f"rings.{extension}")   

    try:
        bot.run(token)
    except Exception as error:
        e = traceback.format_exception(type(error), error, error.__traceback__)
        with open("error.log", "w") as f:
            f.write(str(e))
        
    finally:
        with open("rings/utils/data/settings.json", "w") as outfile:
            json.dump(bot.settings, outfile)
