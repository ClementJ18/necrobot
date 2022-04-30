import discord
from discord.ext import commands

from rings.db import SyncDatabase
from rings.utils.config import token
from rings.utils.utils import get_pre, default_settings
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
    def __init__(self, exts):
        intents = discord.Intents.all()

        super().__init__(
            max_messages=50000,
            fetch_offline_members=True,
            activity=discord.Game("n!help for help"),
            case_insensitive=True,
            description="A bot for managing and enhancing servers",
            command_prefix=get_pre,
            help_command=NecrobotHelp(),
            allowed_mentions=discord.AllowedMentions(everyone=False),
            intents=intents
        )
        
        self.uptime_start = time.time()
        self.counter = datetime.datetime.now().hour
        
        self.version = 3.8
        self.prefixes = ["n!", "N!"]
        self.new_commands = ["flowers", "event", "give", "twitch"]
        self.statuses = ["n!help for help", "currently in {guild} guilds", "with {members} members", "n!report for bug/suggestions"]
        self.perms_name = ["User", "Helper", "Moderator", "Admin Trainee", "Admin", "Server Owner", "Bot Admin", "Bot Dev"]
        self.bot_color = discord.Colour(0x277b0)
        self.url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        self.extension_names = exts

        self.bot_channel = 318465643420712962
        self.error_channel = 415169176693506048
        self.session = None
        self.pool = None
        self.maintenance = True
        self.check_enabled = True
        self.owner_id = 241942232867799040
        
        sync_db = SyncDatabase()
        self.guild_data = sync_db.load_guilds()
        self.polls = sync_db.load_polls()

        self.cat_cache = []
        self.ignored_messages = []
        self.starred = []
        self.potential_stars = {}
        self.reminders = {}
        self.pending_posts = {}
        self.denied_posts = []
        self.events = {}
        self.ongoing_giveaways = {}
        self.queued_posts = None

        with open("rings/utils/data/settings.json", "rb") as infile:
            self.settings = {**default_settings(), **json.load(infile)}
        
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

    @property
    def bot_footer(self):
        return {
            "text": f"Generated by {self.user}", 
            "icon_url": self.user.avatar.replace(format="png", size=128)
        }

    async def setup_hook(self):
        for extension in self.extension_names:
            await self.load_extension(f"rings.{extension}")

        self.loop.create_task(self.meta.load_cache())
        self.queued_posts = asyncio.Queue()
        
    async def invoke(self, ctx):
        if self.maintenance and ctx.command is not None and ctx.author.id != self.owner_id:
            return await ctx.channel.send(":negative_squared_cross_mark: | Maintenance mode engaged, the bot is not currently accepting commands", delete_after=30)
        
        await super().invoke(ctx)
        
    async def wait_for(self, event, *, check=None, timeout=None, handler=None, propagate=True):
        """
        handler : callable
            Function that performs clean up in the case that the timeout is reached
        propagate : bool
            Dictate what happens if an error happens
                True - Error is raised
                None - Nothing
                False - Error is raised but silenced in global error handler
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

    async def confirmation_menu(self, msg, user, cleanup=None):
        emoji_list = ["\N{WHITE HEAVY CHECK MARK}", "\N{NEGATIVE SQUARED CROSS MARK}"]

        def check(reaction, u):
            if user != u or msg.id != reaction.message.id:
                return False

            return str(reaction.emoji) in emoji_list

        if cleanup is None:
            cleanup = msg.clear_reactions

        for emoji in emoji_list:
            await msg.add_reaction(emoji)

        reaction, _ = await self.wait_for(
            "reaction_add", 
            check=check, 
            timeout=300, 
            handler=cleanup, 
            propagate=False
        )

        await msg.clear_reactions()
        return str(reaction.emoji) == "\N{WHITE HEAVY CHECK MARK}"
   
    async def on_error(self, event, *args, **kwargs): 
        """Something has gone wrong so we just try to send a helpful traceback to the channel. If
        the traceback is too big we just send the method/event that errored out and hope that
        the error is obvious."""
        channel = self.get_error_channel()
        
        if isinstance(event, Exception):
            error_traceback = " ".join(traceback.format_exception(type(event), event, event.__traceback__, chain=True))
        else:
            error_traceback = traceback.format_exc()

        embed = discord.Embed(title="Error", description=f"```py\n{error_traceback}\n```", colour=self.bot_color)
        embed.add_field(name='Event', value=event, inline=False)
        embed.set_footer(**self.bot_footer)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            logging.error(error_traceback)
            
    async def on_message(self, message):
        if self.blacklist_check(message.author.id):
            return
            
        if message.type != discord.MessageType.default or message.author.bot:
            return
            
        await self.meta.new_member(message.author, message.guild)

        if self.meta.is_scam(message):
            await self.meta.restrain_scammer(message)
            
        if message.attachments:
            if message.attachments[0].filename.endswith(".bmp"):
                await self.meta.bmp_converter(message)
                
        if message.guild is None:
            tutorial = await self.db.get_tutorial(message.author.id)
            if not tutorial:
                msg = await message.channel.send(":information_source: | Did you know you can delete my messages in DMs by reacting to them with :wastebasket:?")
                await msg.pin()
                await self.db.update_tutorial(message.author.id)
            
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
    'bridge',
    'waifu'
]

bot = NecroBot(exts=extensions)

@bot.check
async def disabled_check(ctx):
    """This is the backbone of the disable command. If the command name is in disabled then
    we check to make sure that it's not an admin trying to invoke it"""
    if ctx.guild is None:
        return True

    disabled = ctx.bot.guild_data[ctx.guild.id]["disabled"]
    if ctx.command.name in disabled and not (await ctx.bot.db.get_permission(ctx.author.id, ctx.guild.id)) > 0:
        raise commands.CheckFailure("This command has been disabled")

    return True      
        
@bot.check
async def allowed_summon(ctx):
    if ctx.guild is None:
        return True
        
    roles = [role.id for role in ctx.author.roles]
    user_id = ctx.author.id
    guild_id = ctx.guild.id

    if user_id in ctx.bot.guild_data[guild_id]["ignore-command"]:
        raise commands.CheckFailure("You are being ignored by the bot")

    if (await ctx.bot.db.get_permission(user_id, guild_id)) > 0:
        return True

    if ctx.channel.id in ctx.bot.guild_data[guild_id]["ignore-command"]:
        raise commands.CheckFailure("Commands not allowed in this channel.")

    if any(x in roles for x in ctx.bot.guild_data[guild_id]["ignore-command"]):
        roles = [f"**{x.name}**" for x in ctx.author.roles if x.id in ctx.bot.guild_data[guild_id]["ignore-command"]]
        raise commands.CheckFailure(f"Roles {', '.join(roles)} aren't allowed to use commands.")

    return True
    
@bot.command(hidden=True)
@commands.is_owner()
async def load(ctx, *extension_names : str):
    """Loads the extension name if in NecroBot's list of rings.
    
    {usage}"""
    for extension_name in extension_names:
        try:
            await bot.load_extension(f"rings.{extension_name}")
            await ctx.send(f"{extension_name} loaded.")
        except commands.ExtensionFailed as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")
        except commands.ExtensionNotFound:
            pass

@bot.command(hidden=True)
@commands.is_owner()
async def unload(ctx, *extension_names : str):
    """Unloads the extension name if in NecroBot's list of rings.
     
    {usage}"""
    for extension_name in extension_names:
        try:
            await bot.unload_extension(f"rings.{extension_name}")
            await ctx.send(f"{extension_name} unloaded.")
        except commands.ExtensionFailed as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")
        except commands.ExtensionNotLoaded:
            pass

@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx, *extension_names : str):
    """Unload and loads the extension name if in NecroBot's list of rings.
     
    {usage}"""
    for extension_name in extension_names:
        try:
            await bot.unload_extension(f"rings.{extension_name}")
        except commands.ExtensionFailed as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")
        except commands.ExtensionNotLoaded:
            pass
            
        try:
            await bot.load_extension(f"rings.{extension_name}")
            await ctx.send(f"{extension_name} reloaded.")
        except commands.ExtensionFailed as e:
            await ctx.send(f"```py\n{type(e).__name__}: {e}\n```")
        except commands.ExtensionNotFound:
            pass

@bot.group(invoke_without_command=True, hidden=True)
@commands.is_owner()
async def off(ctx):
    """Saves all the data and terminate the bot. (Permission level required: 7+ (The Bot Smith))
     
    {usage}"""
    if not bot.maintenance:
        msg = await ctx.send("Shut down in 5 minutes?")
        result = await bot.confirmation_menu(msg, ctx.author)
        if not result:
            return

        bot.maintenance = True                
        task = bot.meta.rotate_status
        tasks_hourly = bot.meta.tasks_hourly
        tasks_hourly.remove(task)

        await bot.change_presence(activity=discord.Game(name="Going down for maintenance soon"))

        await asyncio.sleep(300)
        if not bot.maintenance:
            tasks_hourly.append(task)
            await bot.change_presence(activity=discord.Game(name="n!help for help"))
            return await ctx.send("Shut down aborted.")

    await asyncio.sleep(5)
    await bot.change_presence(activity=discord.Game(name="Bot shutting down...", type=0))
    
    with open("rings/utils/data/settings.json", "w") as file:
        json.dump(bot.settings, file)

    bot.meta.hourly_loop.cancel()
    bot.get_cog("RSS").task.cancel()
    bot.get_cog("Bridge").task.cancel()
    for reminder in bot.reminders.values():
        reminder.cancel()

    await bot.session.close()
    await bot.pool.close()

    await bot.get_bot_channel().send("**Bot Offline**")
    await bot.close()

@off.command(name="abort")
@commands.is_owner()
async def off_abort(ctx):
    bot.maintenance = False
    await ctx.send(":white_check_mark: | Shut down cancelled")

if __name__ == '__main__':
    try:
        bot.run(token)
    except Exception as error:
        tc = traceback.format_exception(type(error), error, error.__traceback__)
        with open("error.log", "w") as f:
            f.write(str(tc))
        
    finally:
        with open("rings/utils/data/settings.json", "w") as outfile:
            json.dump(bot.settings, outfile)
