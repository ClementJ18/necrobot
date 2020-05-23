import discord
from discord.ext import commands

from rings.utils.utils import has_perms, GuildConverter, react_menu, BotError
from rings.utils.config import github_key

try:
    import sh
except ImportError:
    import pbs as sh

import os
import ast
import psutil
import asyncio
from typing import Union, Optional
from simpleeval import simple_eval


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gates = {}
        self.process = psutil.Process()
        
    def insert_returns(self, body):
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)
            ast.fix_missing_locations(body[-1])

        if isinstance(body[-1], ast.If):
            self.insert_returns(body[-1].body)
            self.insert_returns(body[-1].orelse)

        if isinstance(body[-1], ast.With):
            self.insert_returns(body[-1].body)
            
    @commands.command()
    @has_perms(7)
    async def leave(self, ctx, guild : GuildConverter, *, reason : str = None):
        """Leaves the specified server.
        
        {usage}"""
        if reason is not None:
            await guild.owner.send(f"I'm sorry, Necro#6714 has decided I should leave this server, because: {reason}")

        await guild.leave()
        await ctx.send(f":white_check_mark: | I've left {guild.name}")
        
    @commands.command()
    @has_perms(6)
    async def add(self, ctx, user : discord.User, *, equation : str):
        """Does the given pythonic equations on the given user's NecroBot balance.
        `*` - for multiplication
        `+` - for additions
        `-` - for substractions
        `/` - for divisons
        `**` - for exponents
        `%` - for modulo
        More symbols can be used, simply research 'python math symbols'
        
        {usage}
        
        __Example__
        `{pre}add @NecroBot +400` - adds 400 to NecroBot's balance"""
        money = await self.bot.db.get_money(user.id)
        s = f'{money}{equation}'
        try:
            operation = simple_eval(s)
        except (NameError, SyntaxError):
            raise BotError("Operation not recognized.")

        msg = await ctx.send(f":white_check_mark: | Operation successful. Change user balace to **{operation}**?")

        await msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await msg.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        def check(reaction, user):
            return msg.id == reaction.message.id and user == ctx.author and str(reaction.emoji) in ["\N{WHITE HEAVY CHECK MARK}", "\N{NEGATIVE SQUARED CROSS MARK}"]

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=check, timeout=300)
        except asyncio.TimeoutError:
            return await msg.delete()

        if reaction.emoji == "\N{NEGATIVE SQUARED CROSS MARK}":
            await ctx.send(f":white_check_mark: | Cancelled.")
        elif reaction.emoji == "\N{WHITE HEAVY CHECK MARK}":
            await self.bot.db.update_money(user.id, update=operation)
            await ctx.send(":atm: | **{}'s** balance is now **{:,}** :euro:".format(user.display_name, operation))
        
        await msg.delete()
        
        
    @commands.group()
    @has_perms(6)
    async def admin(self, ctx):
        """{usage}"""
        pass
    
    @admin.command(name="permissions", aliases=["perms"])
    @commands.is_owner()
    async def admin_perms(self, ctx, guild : GuildConverter, user : discord.User, level : int):
        """For when regular perms isn't enough.

        {usage}"""
        current_level = await self.bot.db.get_permission(user.id, guild.id)
        if current_level > 5 >= level or level > 5:
            await self.bot.db.update_permission(user.id, update=level)
        else:
            await self.bot.db.update_permission(user.id, guild.id, update=level)

        await ctx.send(f":white_check_mark: | All good to go, **{user.display_name}** now has permission level **{level}** on server **{guild.name}**")

    @admin.command(name="disable")
    @has_perms(6)
    async def admin_disable(self, ctx, *, command : str):
        """For when regular disable isn't enough. Disables command discord-wide.

        {usage}
        """
        command = self.bot.get_command(command)
        if command.enabled:
            command.enabled = False
            self.bot.settings["disabled"].append(command.name)
            await ctx.send(f":white_check_mark: | Disabled **{command.name}**")
        else:
            raise BotError(f"Command **{command.name}** already disabled")
            
    @admin.command(name="enable")
    @has_perms(6)
    async def admin_enable(self, ctx, *, command : str):
        """For when regular enable isn't enough. Re-enables the command discord-wide.

        {usage}
        """
        command = self.bot.get_command(command)
        if command.enabled:
            raise BotError(f"Command **{command.name}** already enabled")

        command.enabled = True
        self.bot.settings["disabled"].remove(command.name)
        await ctx.send(f":white_check_mark: | Enabled **{command.name}**")
            
    @commands.command()
    @has_perms(6)
    async def pm(self, ctx, user : discord.User, *, message : str):
        """Sends the given message to the user of the given id. It will then wait for an answer and 
        print it to the channel it was called it. 
        
        {usage}
        
        __Example__
        `{pre}pm 34536534253Z6 Hello, user` - sends 'Hello, user' to the given user id and waits for a reply"""
        await user.send(message)
        to_edit = await ctx.send(":white_check_mark: | **Message sent**")

        def check(m):
            return m.author == user and m.channel == user

        msg = await self.bot.wait_for("message", check=check, timeout=6000)
        await to_edit.edit(content=f":speech_left: | **User: {msg.author}** said :**{msg.content[1950:]}**")
        
    @commands.command()
    @commands.is_owner()
    async def get(self, ctx, obj_id : int):
        """Returns the name of the user or server based on the given id. Used to debug errors. 
        (
        
        {usage}
        
        __Example__
        `{pre}get 345345334235345` - returns the user or server name with that id"""
        msg = await ctx.send("Scanning...")
        user = self.bot.get_user(obj_id)
        if user:
            await msg.edit(content=f"User: **{user}**")
            return

        await msg.edit(content="User with that ID not found.")

        guild = self.bot.get_guild(obj_id)
        if guild:
            await msg.edit(content=f"Server: **{guild}**")
            return

        await msg.edit(content="Server with that ID not found")

        channel = self.bot.get_channel(obj_id)
        if channel:
            await msg.edit(content=f"Channel: **{channel.name}** on **{channel.guild.name}** ({channel.guild.id})")
            return

        await msg.edit(content="Channel with that ID not found")

        role = discord.utils.get([item for sublist in  [guild.roles for guild in self.bot.guilds] for item in sublist], id=obj_id)
        if role:
            await msg.edit(content=f"Role: **{role.name}** on **{role.guild.name}** ({role.guild.id})")
            return

        await msg.edit(content="Nothing found with that ID")
        
    @commands.command()
    @commands.is_owner()
    async def invites(self, ctx, *, guild : GuildConverter = None):
        """Returns invites (if the bot has valid permissions) for each server the bot is on if no guild id is specified. 
        (
        
        {usage}"""
        async def get_invite(guild):
            try:
                invite = await guild.invites()[0]
                return f"Server: {guild.name}({guild.id}) - <{invite.url}>"
            except (discord.Forbidden, IndexError) as e:
                return f"Server: {guild.name}({guild.id}) - <{e}>"

        if guild:
            await ctx.send(await get_invite(guild))
        else:
            await ctx.send("\n".join([await get_invite(guild) for guild in self.bot.guilds]))
            
    @commands.command()
    @commands.is_owner()
    async def debug(self, ctx, *, cmd : str):
        """Evaluates code. (
        
        {usage}
        
        The following global envs are available:
            `bot`: bot instance
            `discord`: discord module
            `commands`: discord.ext.commands module
            `ctx`: Context instance
            `__import__`: allows to import module
            `guild`: guild eval is being invoked in
            `channel`: channel eval is being invoked in
            `author`: user invoking the eval
        """
        fn_name = "_eval_expr"
        cmd = cmd.strip("` ")
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
        body = f"async def {fn_name}():\n{cmd}"
        python = '```py\n{}\n```'

        env = {
            'bot': ctx.bot,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__,
            'guild': ctx.guild,
            'channel': ctx.channel,
            'author': ctx.author
        }

        try:
            parsed = ast.parse(body)
            body = parsed.body[0].body
            self.insert_returns(body)

            exec(compile(parsed, filename="<ast>", mode="exec"), env)
            result = (await eval(f"{fn_name}()", env))
            if result is not None and result != "":
                await ctx.send(result)
            else:
                await ctx.send(":white_check_mark:")
        except Exception as e:
            await ctx.send(python.format(f'{type(e).__name__}: {e}'))
            
    @commands.command()
    @has_perms(6)
    async def logs(self, ctx, start : Optional[int] = 0, *arguments):
        """Get a list of commands. SQL arguments can be passed to filter the output.

        {usage}"""
        if arguments:
            raw_args = " AND ".join(arguments)
            sql = f"SELECT user_id, command, guild_id, message, time_used, can_run FROM necrobot.Logs WHERE {raw_args} ORDER BY time_used DESC"
        else:
            sql = "SELECT user_id, command, guild_id, message, time_used, can_run FROM necrobot.Logs ORDER BY time_used DESC"

        results = await self.bot.query_executer(sql)

        def embed_maker(pages, entries):
            page, max_page = pages
            
            embed = discord.Embed(title="Command Log", colour=discord.Colour(0x277b0), description=f"{page}/{max_page}")
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
            for row in entries:
                user = self.bot.get_user(row["user_id"])
                guild = self.bot.get_guild(row["guild_id"])
                embed.add_field(name=row["command"], value=f"From {user} ({user.id}) on {guild} ({guild.id}) on {row['time_used']}\n **Message**\n{row['message'][:1000]}", inline=False)

            return embed

        await react_menu(ctx, results, 5, embed_maker, page=start)
        
    @commands.command(name="as")
    @commands.is_owner()
    async def _as(self, ctx, user : discord.Member, *, message : str):
        """Call a command as another user, used for debugging purposes

        {usage}

        __Examples__
        `{pre}as NecroBot n!balance` - calls the balance command as though necrobot had called it (displaying its balance).

        """
        if ctx.command == "as":
            return

        ctx.message.author = user
        ctx.message.content = message

        await self.bot.process_commands(ctx.message)
        
    @commands.command()
    async def stats(self, ctx):
        """Provides meta data on the bot.

        {usage}"""
        
        headers = {"Authorization": f"token {github_key}"}
        emojis = {"dnd": "<:dnd:509069576160542757>", "idle": "<:away:509069596930736129>", "offline": "<:offline:509069561065111554>", "online": "<:online:509069615494725643>"}
        async with self.bot.session.get("https://api.github.com/repos/ClementJ18/necrobot/commits", headers=headers) as r:
            resp = (await r.json())[:5]

        description = "\n".join([f"[`{c['sha'][:7]}`]({c['url']}) - {c['commit']['message']}" for c in resp])
        embed = discord.Embed(title="Information", colour=discord.Colour(0x277b0), description=description)
        embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))

        members = {x : set() for x in discord.Status if x != discord.Status.invisible}
        for user in self.bot.get_all_members():
            if user.status == discord.Status.invisible:
                continue
            members[user.status].add(user.id)

        embed.add_field(name="Members", value="\n".join([f"{emojis[key.name]} {len(value)}" for key, value in members.items()]), inline=False)
        memory_usage = self.process.memory_full_info().uss / 1024**2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU', inline=False)

        await ctx.send(embed=embed)
        
    @commands.command()
    @has_perms(6)
    async def gate(self, ctx, channel : Union[discord.TextChannel, discord.User]):
        """Connects two channels with a magic gate so that users on both servers can communicate. Magic:tm:

        {usage}

        """
        if channel == ctx.channel:
            raise BotError("Gate destination cannnot be the same as channel the command is called from")

        await channel.send(":gate: | A warp gate has opened on your server, you are now in communication with a Necrobot admin. Voice any concerns without fear.")
        await ctx.send(f":gate: | I've opened a gate to {channel.mention}")

        self.gates[ctx.channel.id] = channel
        self.gates[channel.id] = ctx.channel

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and message.content == "n!exit"


        await self.bot.wait_for("message", check=check)

        await channel.send(":stop: | The NecroBot admin has ended the conversation.")
        await ctx.send(":stop: | Conversation ended")

        del self.gates[ctx.channel.id]
        del self.gates[channel.id] 
        
    @commands.command()
    @has_perms(6)
    async def feeds(self, ctx):
        """Get info on all the feeds managed on this server.

        {usage}
        """
        ps = sh.grep(sh.ps("-ef"), 'python3.6')
        
        feeds_dict = {
            "main.py": {
                "name": "Confessions", 
                "command": "nohup sudo python3.6 /home/pi/cardiff_confessions/main.py&",
                "emote": "\N{HEAR-NO-EVIL MONKEY}"
            },
            "rss.py": {
                "name": "RSS Feeds", 
                "command": "nohup sudo python3.6 /home/pi/feeds/rss.py&",
                "emote": "\N{OPEN MAILBOX WITH RAISED FLAG}"
            },
            "log.py": {
                "name": "ModDB Logger", 
                "command": "nohup sudo python3.6 /home/pi/edain/log.py&",
                "emote": "\N{CHART WITH DOWNWARDS TREND}"
            }
        }

        up = [key for key, value in feeds_dict.items() if key in ps]
        down = [key for key, value in feeds_dict.items() if not key in ps]

        string = f"__Status on the systems__\n**Online**: {', '.join([feeds_dict[key]['name'] for key in up])}\n**Offline**: {', '.join([feeds_dict[key]['name'] for key in down])}"
        msg = await ctx.send(string)

        allowed = []
        for key in down:
            emote = feeds_dict[key]["emote"]
            allowed.append(emote)
            await msg.add_reaction(emote)

        reaction, _ = await self.bot.wait_for("reaction_add", check=lambda reaction, user: user == ctx.author and reaction.channel == ctx.channel and reaction.emoji in allowed)

        await msg.clear_reactions()

        if reaction.emoji == "\N{CHART WITH DOWNWARDS TREND}":
            os.system("nohup sudo python3.6 /home/pi/edain/log.py&")
        elif reaction.emoji == "\N{OPEN MAILBOX WITH RAISED FLAG}":
            os.system("nohup sudo python3.6 /home/pi/feeds/rss.py&")
        elif reaction.emoji == "\N{HEAR-NO-EVIL MONKEY}":
            os.system("nohup sudo python3.6 /home/pi/cardiff_confessions/main.py&")
            
    @admin.command(name="badges")
    @has_perms(6)
    async def admin_badges(self, ctx, subcommand : str, user : discord.User, badge : str):
        """Used to grant special badges to users. Uses add/delete subcommand

        {usage}
        """
        badges = [x["name"] for x in await self.bot.db.get_badge_shop()]
        if badge not in badges:
            raise BotError("Not a valid badge")

        if subcommand not in ("add", "delete"):
            raise BotError("Not a valid subcommand")

        has_badge = await self.bot.db.get_badges(user.id, badge)
        if subcommand == "add" and not badge:
            await self.bot.db.insert_badge(user.id, badge) 
            await ctx.send(f":white_check_mark: | Granted the **{badge}** badge to user **{user}**")
        elif subcommand == "delete" and badge:
            await self.bot.db.delete_badge(user.id, badge) 
            await ctx.send(f":white_check_mark: | Reclaimed the **{badge}** badge from user **{user}**")
        else:
            raise BotError("Users has/doesn't have the badge")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id in self.gates:
            channel = self.gates[message.channel.id]
        elif message.author.id in self.gates:
            channel = self.gates[message.author.id]
        else:
            return
        
        message.content = message.content.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        embed = discord.Embed(title="Message", description=message.content)
        embed.set_author(name=message.author, icon_url=message.author.avatar_url_as(format="png", size=128))
        embed.set_footer(text="Generated by NecroBot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
        
        await channel.send(embed=embed)
        
def setup(bot):
    bot.add_cog(Admin(bot))
