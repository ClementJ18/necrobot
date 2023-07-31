from __future__ import annotations

import ast
import datetime
import traceback
from typing import TYPE_CHECKING, Dict, Literal, Union

import discord
import psutil
from discord.ext import commands
from pyparsing import List
from simpleeval import simple_eval

from rings.utils.checks import has_perms
from rings.utils.converters import (
    BadgeConverter,
    Grudge,
    GuildConverter,
    MemberConverter,
    RangeConverter,
    UserConverter,
)
from rings.utils.ui import Confirm, Paginator
from rings.utils.utils import BotError

if TYPE_CHECKING:
    from bot import NecroBot


class Admin(commands.Cog):
    def __init__(self, bot: NecroBot):
        self.bot = bot
        self.gates = {}
        self.process = psutil.Process()

    #######################################################################
    ## Functions
    #######################################################################

    def insert_returns(self, body):
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)
            ast.fix_missing_locations(body[-1])

        if isinstance(body[-1], ast.If):
            self.insert_returns(body[-1].body)
            self.insert_returns(body[-1].orelse)

        if isinstance(body[-1], ast.With):
            self.insert_returns(body[-1].body)

    def cleanup_code(self, content):
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        return content.strip("`")

    #######################################################################
    ## Commands
    #######################################################################

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    async def grudge(
        self,
        ctx: commands.Context[NecroBot],
        user: discord.User = commands.parameter(converter=UserConverter),
        *,
        grudge: str = commands.parameter(),
    ):
        """Add a grudge

        {usage}"""
        channel = self.bot.get_channel(723281310235492503)

        embed = discord.Embed(title="Grudge Record", colour=self.bot.bot_color, description=grudge)
        embed.add_field(name="User", value=f"{user} ({user.id})")
        embed.add_field(name="Date", value=datetime.date.today().strftime("%A %-d of %B, %Y"))
        embed.set_footer(**self.bot.bot_footer)

        await channel.send(embed=embed)
        await ctx.send(embed=embed)

        await self.bot.db.query(
            "INSERT INTO necrobot.Grudges(user_id, name, grudge) VALUES($1, $2, $3)",
            user.id,
            str(user),
            grudge,
        )

    @grudge.command(name="list")
    async def grudge_list(self, ctx: commands.Context[NecroBot], user: Union[UserConverter, int]):
        """See all the grudges for a user

        {usage}
        """
        if isinstance(user, discord.User):
            user = user.id

        grudges = await self.bot.db.query(
            "SELECT * FROM necrobot.Grudges WHERE user_id = $1", user
        )

        def embed_maker(view: Paginator, entries: List[Dict[str, str]]):
            if self.bot.get_user(user):
                name = str(self.bot.get_user(user))
            elif entries:
                name = entries[0][2]
            else:
                name = user

            embed = discord.Embed(
                title=f"Grudges ({view.page_string})",
                colour=self.bot.bot_color,
                description=f"List of grudges for {name}",
            )

            embed.set_footer(**self.bot.bot_footer)

            for entry in entries:
                embed.add_field(name=entry[0], value=entry[3][:500])

            return embed

        await Paginator(embed_maker, 10, grudges, ctx.author).start(ctx)

    @grudge.command(name="info")
    async def grudge_info(self, ctx: commands.Context[NecroBot], grudge: Grudge):
        """Get the full info about a specific grudge

        {usage}"""
        if self.bot.get_user(grudge[1]):
            name = str(self.bot.get_user(grudge[1]))
        else:
            name = grudge[2]

        embed = discord.Embed(
            title=f"Grudge `{grudge[0]}`",
            colour=self.bot.bot_color,
            description=grudge[3],
        )
        embed.add_field(name="User", value=f"{name} ({grudge[1]})")
        embed.add_field(name="Date", value=grudge[4].strftime("%A %-d of %B, %Y"))
        embed.add_field(name="Avenged", value=str(grudge[5]))
        embed.set_footer(**self.bot.bot_footer)

        await ctx.send(embed=embed)

    @grudge.command(name="settle")
    @commands.is_owner()
    async def grudge_settle(
        self, ctx: commands.Context[NecroBot], grudge: Grudge, settlement: str = True
    ):
        """Mark a grudge as settled

        {usage}"""
        await self.bot.db.query(
            "UPDATE necrobot.Grudges SET avenged = $1 WHERE id = $2",
            str(settlement),
            grudge["id"],
        )
        await ctx.send(
            ":white_check_mark: | Grudge `{grudge['id']}` has been considered as settled"
        )

    @commands.command()
    @has_perms(7)
    async def leave(
        self,
        ctx: commands.Context[NecroBot],
        guild: discord.Guild = commands.parameter(converter=GuildConverter),
    ):
        """Leaves the specified server.

        {usage}"""
        await guild.leave()
        await ctx.send(f":white_check_mark: | I've left {guild.name}")

    @commands.command()
    @has_perms(6)
    async def add(
        self,
        ctx: commands.Context[NecroBot],
        user: discord.User = commands.parameter(converter=UserConverter),
        *,
        equation: str = commands.parameter(),
    ):
        """Does the given pythonic equations on the given user's NecroBot balance.
        `*` - for multiplication
        `+` - for additions
        `-` - for substractions
        `/` - for divisons
        `**` - for exponents
        `%` - for modulo

        {usage}

        __Example__
        `{pre}add @NecroBot m+400` - adds 400 to NecroBot's balance"""
        money = await self.bot.db.get_money(user.id)
        s = equation.replace("m", str(money))
        try:
            operation = simple_eval(s)
        except (NameError, SyntaxError) as e:
            raise BotError("Operation not recognized.") from e

        view = Confirm(
            ctx.author,
            confirm_msg=":atm: | **{}'s** balance is now **{:,}** :euro:".format(
                user.display_name, operation
            ),
            cancel_msg=":white_check_mark: | Cancelled.",
        )

        view.message = await ctx.send(
            f":white_check_mark: | Operation successful. Change {user} balance to **{operation}**?",
            view=view,
        )
        await view.wait()
        if not view.value:
            return

        await self.bot.db.update_money(user.id, update=operation)

    @commands.group()
    async def admin(self, ctx: commands.Context[NecroBot]):
        """{usage}"""
        pass

    @admin.command(name="permissions", aliases=["perms"])
    @commands.check_any(commands.is_owner(), has_perms(6))
    async def admin_perms(
        self,
        ctx: commands.Context[NecroBot],
        guild: discord.Guild = commands.parameter(converter=GuildConverter),
        user: discord.User = commands.parameter(converter=UserConverter),
        level: int = commands.parameter(),
    ):
        """For when regular perms isn't enough.

        {usage}"""
        current_level = await self.bot.db.get_permission(user.id, guild.id)
        if current_level > 5 >= level or level > 5:
            await self.bot.db.update_permission(user.id, update=level)
        else:
            await self.bot.db.update_permission(user.id, guild.id, update=level)

        await ctx.send(
            f":white_check_mark: | All good to go, **{user.display_name}** now has permission level **{level}** on server **{guild.name}**"
        )

    @admin.command(name="disable")
    @commands.check_any(commands.is_owner(), has_perms(6))
    async def admin_disable(self, ctx: commands.Context[NecroBot], *, command: str):
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
    @commands.check_any(commands.is_owner(), has_perms(6))
    async def admin_enable(self, ctx: commands.Context[NecroBot], *, command: str):
        """For when regular enable isn't enough. Re-enables the command discord-wide.

        {usage}
        """
        command = self.bot.get_command(command)
        if command.enabled:
            raise BotError(f"Command **{command.name}** already enabled")

        command.enabled = True
        self.bot.settings["disabled"].remove(command.name)
        await ctx.send(f":white_check_mark: | Enabled **{command.name}**")

    @admin.command(name="badges")
    @commands.check_any(commands.is_owner(), has_perms(6))
    async def admin_badges(
        self,
        ctx: commands.Context[NecroBot],
        subcommand: Literal["add", "delete"],
        user: discord.User = commands.parameter(converter=UserConverter),
        badge: BadgeConverter = commands.parameter(),
        spot: RangeConverter(1, 8) = None,
    ):
        """Used to grant special badges to users. Uses add/delete subcommand

        {usage}
        """
        has_badge = await self.bot.db.get_badges(user.id, badge=badge["name"])
        if subcommand == "add" and not has_badge:
            await self.bot.db.insert_badge(user.id, badge["name"])
            if spot is None:
                await ctx.send(
                    f":white_check_mark: | Granted the **{badge['name']}** badge to user **{user}**"
                )
            else:
                await self.bot.db.update_spot_badge(user.id, spot, badge["name"])
                await ctx.send(
                    f":white_check_mark: | Granted the **{badge['name']}** badge to user **{user}** and placed it on spot **{spot}**"
                )
        elif subcommand == "delete" and has_badge:
            await self.bot.db.delete_badge(user.id, badge["name"])
            await ctx.send(
                f":white_check_mark: | Reclaimed the **{badge['name']}** badge from user **{user}**"
            )
        else:
            raise BotError("Users has/doesn't have the badge")

    @admin.command(name="blacklist")
    @commands.is_owner()
    async def admin_blacklist(self, ctx: commands.Context[NecroBot], object_id: int):
        """Blacklist a user

        {usage}
        """
        if object_id in self.bot.settings["blacklist"]:
            self.bot.settings["blacklist"].remove(object_id)
            await ctx.send(":white_check_mark: | Pardoned")
        else:
            self.bot.settings["blacklist"].append(object_id)
            await ctx.send(":white_check_mark: | Blacklisted")

    @commands.command()
    @has_perms(6)
    async def pm(
        self,
        ctx: commands.Context[NecroBot],
        user: discord.User = commands.parameter(converter=UserConverter),
        *,
        message: str = commands.parameter(),
    ):
        """Sends the given message to the user of the given id. It will then wait for an answer and \
        print it to the channel it was called it.

        {usage}

        __Example__
        `{pre}pm 34536534253Z6 Hello, user` - sends 'Hello, user' to the given user id and waits for a reply"""
        await user.send(message)
        to_edit = await ctx.send(":white_check_mark: | **Message sent**")

        def check(m):
            return m.author == user and m.channel == user

        msg = await self.bot.wait_for("message", check=check, timeout=6000, propagate=False)

        await to_edit.edit(
            content=f":speech_left: | **User: {msg.author}** said :**{msg.content[1950:]}**"
        )

    @commands.command()
    @has_perms(6)
    async def get(self, ctx: commands.Context[NecroBot], obj_id: int):
        """Returns the name of the user or server based on the given id. Used to debug errors.

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
            await msg.edit(
                content=f"Channel: **{channel.name}** on **{channel.guild.name}** ({channel.guild.id})"
            )
            return

        await msg.edit(content="Channel with that ID not found")

        role = discord.utils.get(
            [item for sublist in [guild.roles for guild in self.bot.guilds] for item in sublist],
            id=obj_id,
        )
        if role:
            await msg.edit(
                content=f"Role: **{role.name}** on **{role.guild.name}** ({role.guild.id})"
            )
            return

        await msg.edit(content="Nothing found with that ID")

    @commands.command()
    @commands.is_owner()
    async def invites(
        self,
        ctx: commands.Context[NecroBot],
        *,
        guild: discord.Guild = commands.parameter(converter=GuildConverter, default=None),
    ):
        """Returns invites (if the bot has valid permissions) for each server the bot is on if no \
        guild id is specified.

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
    async def debug(self, ctx: commands.Context[NecroBot], *, cmd: str):
        """Evaluates code.

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
        cmd = self.cleanup_code(cmd)
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
        body = f"async def {fn_name}():\n{cmd}"

        env = {
            "bot": ctx.bot,
            "discord": discord,
            "commands": commands,
            "ctx": ctx,
            "__import__": __import__,
            "guild": ctx.guild,
            "channel": ctx.channel,
            "author": ctx.author,
        }

        parsed = ast.parse(body)
        body = parsed.body[0].body
        self.insert_returns(body)

        try:
            exec(compile(parsed, filename="<ast>", mode="exec"), env)
            result = await eval(f"{fn_name}()", env)
        except Exception as e:
            error_traceback = " ".join(
                traceback.format_exception(type(e), e, e.__traceback__, chain=True)
            )
            embed = discord.Embed(description=f"```py\n{error_traceback}\n```")
            return await ctx.send(embed=embed)

        if result is not None and result != "":
            await ctx.send(result)
        else:
            await ctx.send(":white_check_mark:")

    @commands.command()
    @has_perms(6)
    async def logs(self, ctx: commands.Context[NecroBot], *arguments):
        """Get a list of commands. SQL arguments can be passed to filter the output.

        {usage}"""
        if arguments:
            raw_args = " AND ".join(arguments)
            sql = f"SELECT user_id, command, guild_id, message, time_used, can_run FROM necrobot.Logs WHERE {raw_args} ORDER BY time_used DESC"
        else:
            sql = "SELECT user_id, command, guild_id, message, time_used, can_run FROM necrobot.Logs ORDER BY time_used DESC"

        results = await self.bot.db.query(sql)

        def embed_maker(view: Paginator, entries: List[Dict[str, str]]):

            embed = discord.Embed(
                title="Command Log",
                colour=self.bot.bot_color,
                description=f"{view.page_string}",
            )
            embed.set_footer(**self.bot.bot_footer)
            for row in entries:
                user = self.bot.get_user(row["user_id"])
                guild = self.bot.get_guild(row["guild_id"])
                embed.add_field(
                    name=row["command"],
                    value=f"From {user} ({row['user_id']}) on {guild} ({row['guild_id']}) on {row['time_used']}\n **Message**\n{row['message'][:1000]}",
                    inline=False,
                )

            return embed

        await Paginator(embed_maker, 5, results, ctx.author).start(ctx)

    @commands.command(name="as")
    @commands.is_owner()
    async def _as(
        self,
        ctx: commands.Context[NecroBot],
        user: discord.Member = commands.parameter(converter=MemberConverter),
        *,
        message: str = commands.parameter(),
    ):
        """Call a command as another user, used for debugging purposes

        {usage}

        __Examples__
        `{pre}as NecroBot {pre}balance` - calls the balance command as though necrobot had called it (displaying its balance).

        """
        if ctx.command == "as":
            return

        ctx.message.author = user
        ctx.message.content = message

        await self.bot.process_commands(ctx.message)

    @commands.command()
    @has_perms(6)
    async def gate(
        self,
        ctx: commands.Context[NecroBot],
        channel: Union[discord.TextChannel, discord.Thread, UserConverter],
    ):
        """Connects two channels with a magic gate so that users on both servers can communicate. Magic:tm:

        {usage}

        """
        if channel == ctx.channel:
            raise BotError(
                "Gate destination cannot be the same as channel the command is called from"
            )

        await channel.send(
            ":gate: | A warp gate has opened on your server, you are now in communication with a Necrobot admin. Voice any concerns without fear."
        )
        await ctx.send(f":gate: | I've opened a gate to {channel.mention}")

        self.gates[ctx.channel.id] = channel
        self.gates[channel.id] = ctx.channel

        def check(message: discord.Message):
            return (
                message.author == ctx.author
                and message.channel == ctx.channel
                and message.content == "n!exit"
            )

        await self.bot.wait_for("message", check=check, propagate=None)

        await channel.send(":stop: | The NecroBot admin has ended the conversation.")
        await ctx.send(":stop: | Conversation ended")

        del self.gates[ctx.channel.id]
        del self.gates[channel.id]

    #######################################################################
    ## Events
    #######################################################################

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id in self.gates:
            channel = self.gates[message.channel.id]
        elif message.author.id in self.gates:
            channel = self.gates[message.author.id]
        else:
            return

        message.content = message.content.replace("@everyone", "@\u200beveryone").replace(
            "@here", "@\u200bhere"
        )
        embed = discord.Embed(title="Message", description=message.content)
        embed.set_author(
            name=message.author,
            icon_url=message.author.display_avatar.replace(format="png", size=128),
        )
        embed.set_footer(**self.bot.bot_footer)

        await channel.send(embed=embed)


async def setup(bot: NecroBot):
    await bot.add_cog(Admin(bot))
