from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Callable, Dict, List, Union

import discord
from discord.ext import commands

from rings.utils.checks import has_perms
from rings.utils.converters import (
    MemberConverter,
    RangeConverter,
    RoleConverter,
    TimeConverter,
    WritableChannelConverter,
    transform_mentions,
)
from rings.utils.ui import (
    Confirm,
    EmbedDefaultConverter,
    EmbedRangeConverter,
    EmbedStringConverter,
    MultiInputEmbedView,
    Paginator,
    PollEditorView,
)
from rings.utils.utils import POSITIVE_CHECK, BotError, DatabaseError, build_format_dict, check_channel

if TYPE_CHECKING:
    from bot import NecroBot


class GivemePaginator(Paginator):
    @discord.ui.select(options=[discord.SelectOption(label="Placeholder")], min_values=0, max_values=1)
    async def select_role(self, interaction: discord.Interaction[NecroBot], select: discord.ui.Select):
        entries: List[discord.Role] = self.get_entry_subset()

        roles_to_add = [interaction.guild.get_role(int(role_id)) for role_id in select.values]
        roles_to_remove = [
            interaction.user.get_role(role.id)
            for role in entries
            if interaction.user.get_role(role.id) and str(role.id) not in select.values
        ]

        if roles_to_add:
            await interaction.user.add_roles(*roles_to_add)

        if roles_to_remove:
            await interaction.user.remove_roles(*roles_to_remove)

        self.view_maker(entries)
        await interaction.response.edit_message(embed=await self.generate_embed(entries), view=self)
        if roles_to_add or roles_to_remove:
            await interaction.followup.send(f"{POSITIVE_CHECK} | Roles updated", ephemeral=True)

    def view_maker(self, entries: List[discord.Role]):
        self.select_role.options = [
            discord.SelectOption(
                label=role.name, value=role.id, default=self.author.get_role(role.id) is not None
            )
            for role in entries
        ]
        self.select_role.max_values = len(self.select_role.options)


class Server(commands.Cog):
    """Contains all the commands related to customising Necrobot's behavior on your server and to your server members. Contains
    commands for stuff such as setting broadcast, giving users permissions, ignoring users, getting info on your current settings,
    ect..."""

    def __init__(self, bot: NecroBot):
        self.bot = bot

    #######################################################################
    ## Cog Functions
    #######################################################################

    def cog_check(self, ctx: commands.Context[NecroBot]):
        if ctx.guild:
            return True

        raise commands.CheckFailure("This command cannot be used in private messages.")

    #######################################################################
    ## Functions
    #######################################################################

    def get_all(self, ctx: commands.Context[NecroBot], entries):
        l = []
        for x in entries:
            channel = ctx.guild.get_channel(x)
            if channel:
                l.append(f"C: {channel.name}")
                continue

            member = ctx.guild.get_member(x)
            if member:
                l.append(f"U: {member.name}")
                continue

            role = ctx.guild.get_role(x)
            if role:
                l.append(f"R: {role.name}")
                continue

        return l

    async def update_binding(self, role):
        roles = await self.bot.db.query(
            "SELECT * FROM necrobot.PermissionRoles WHERE guild_id=$1", role.guild.id
        )

        counter = 0
        for member in role.members:
            try:
                level = max(
                    [
                        x["level"]
                        for x in roles
                        if x["role_id"] != role.id and x["role_id"] in [x.id for x in member.roles]
                    ]
                )
            except ValueError:
                level = 0

            updated = await self.bot.db.query(
                "UPDATE necrobot.Permissions SET level=$1 WHERE user_id=$2 AND guild_id=$3 AND level <= 4 RETURNING user_id",
                level,
                member.id,
                role.guild.id,
                fetchval=True,
            )

            if updated:
                counter += 1

        return counter

    #######################################################################
    ## Commands
    #######################################################################

    @commands.group(invoke_without_command=True, aliases=["perms"])
    @has_perms(4)
    async def permissions(
        self,
        ctx: commands.Context[NecroBot],
        user: Annotated[discord.Member, MemberConverter] = None,
        level: RangeConverter(0, 7) = None,
    ):
        """Sets the NecroBot permission level of the given user, you can only set permission levels lower than your own. \
        Permissions reset if you leave the server.

        {usage}

        __Example__
        `{pre}permissions @NecroBot 5` - set the NecroBot permission level to 5
        `{pre}perms @NecroBot 5` - set the NecroBot permission level to 5"""
        if level is None and user is not None:
            level = await self.bot.db.get_permission(user.id, ctx.guild.id)
            return await ctx.send(f"**{user.display_name}** is **{level}** ({self.bot.perms_name[level]})")

        if level is None and user is None:
            members = await self.bot.db.query(
                "SELECT user_id, level FROM necrobot.Permissions WHERE level > 0 AND guild_id = $1 ORDER BY level DESC",
                ctx.guild.id,
            )

            def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
                string = ""
                for member in entries:
                    name = ctx.guild.get_member(member[0]).mention
                    level = member[1]

                    string += f"\n -**{name}**: {level} ({self.bot.perms_name[level]})"

                embed = discord.Embed(
                    title="Permissions on the server",
                    description=string,
                    colour=self.bot.bot_color,
                )
                embed.set_footer(**self.bot.bot_footer)
                return embed

            return await Paginator(10, members, ctx.author, embed_maker=embed_maker).start(ctx)

        if await self.bot.db.compare_user_permission(ctx.author.id, ctx.guild.id, user.id) > 1:
            current_level = await self.bot.db.get_permission(user.id, ctx.guild.id)

            if current_level == level:
                raise BotError("The user already has that permission level")

            await self.bot.db.update_permission(user.id, ctx.guild.id, update=level)

            if current_level < level:
                await ctx.send(
                    f"{POSITIVE_CHECK} | **{user.display_name}** has been promoted to **{self.bot.perms_name[level]}** ({level})"
                )
            else:
                await ctx.send(
                    f"{POSITIVE_CHECK} | **{user.display_name}** has been demoted to **{self.bot.perms_name[level]}** ({level})"
                )

        else:
            raise BotError("You do not have the required NecroBot permission to grant this permission level")

    @permissions.command(name="commands")
    @has_perms(1)
    async def permissions_commands(self, ctx: commands.Context[NecroBot], level: RangeConverter(1, 7)):
        """See what permission level has access to which commands

        {usage}

        """
        c = []
        for command in self.bot.commands:
            if command.hidden:
                continue

            perms_check = discord.utils.find(lambda x: x.__qualname__.startswith("has_perms"), command.checks)
            if perms_check is not None and perms_check.level <= level:
                c.append(f"- {command.name} ({perms_check.level}+)")

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            string = "\n".join(entries)
            embed = discord.Embed(
                title=f"Commands for {self.bot.perms_name[level]} {level}+ ({view.page_string})",
                colour=self.bot.bot_color,
                description=string,
            )

            embed.set_footer(**self.bot.bot_footer)
            return embed

        await Paginator(10, c, ctx.author, embed_maker=embed_maker).start(ctx)

    @permissions.command(name="bind")
    @has_perms(4)
    async def permissions_bind(
        self,
        ctx: commands.Context[NecroBot],
        level: RangeConverter(1, 4) = None,
        role: Annotated[discord.Role, RoleConverter] = None,
    ):
        """See current bindings, create a binding or remove a binding. Bindings between a role and a level mean that \
        the bot automatically assigns that permission level to the users when they are given the role (if it is higher \
        than their current).

        Bindings do not work if the bot is offline and the bot will not retro-actively apply them when it comes back online.

        {usage}

        __Examples__
        `{pre}perms bind 2 Trainee` - create a binding for permission level 2 with the role Trainee
        `{pre}perms bind 2` - remove the binding between the permission level 2 and the role it is currently tied to
        `{pre}perms bind` - seel all bindings
        """

        # show information
        if level is None:
            roles = await self.bot.db.query(
                "SELECT * FROM necrobot.PermissionRoles WHERE guild_id=$1", ctx.guild.id
            )

            if not roles:
                raise BotError("No bindings on this server")

            string = ""
            for r in roles:
                string += f"- {ctx.guild.get_role(r[2]).mention}: {self.bot.perms_name[r[1]]} ({r[1]})\n"

            embed = discord.Embed(
                title="Roles tied to permissions",
                description=string,
                colour=self.bot.bot_color,
            )
            embed.set_footer(**self.bot.bot_footer)

            return await ctx.send(embed=embed)

        # remove binding
        if role is None:
            role_id = await self.bot.db.query(
                "DELETE FROM necrobot.PermissionRoles WHERE guild_id = $1 AND level = $2 RETURNING role_id",
                ctx.guild.id,
                level,
                fetchval=True,
            )

            if role_id:
                role = ctx.guild.get_role(role_id)
                if not role.members:
                    return await ctx.send(f"{POSITIVE_CHECK} | Removed permission link!")

                view = Confirm(ctx.author)
                view.message = await ctx.send(
                    f"{POSITIVE_CHECK} | Removed permission link! Re-calculate permissions of members with the role? (This can take a while based on the number of members with the role)",
                    view=view,
                )
                await view.wait()
                if not view.value:
                    return

                counter = await self.update_bindings(role)
                return await view.message.edit(
                    content=f"{POSITIVE_CHECK} | Permissions of **{counter}** member(s) updated"
                )

            raise BotError("No role set for that permission level")

        # add binding
        try:
            await self.bot.db.query(
                "INSERT INTO necrobot.PermissionRoles VALUES($1, $2, $3)",
                ctx.guild.id,
                level,
                role.id,
                fetchval=True,
            )
        except DatabaseError as e:
            raise BotError(
                "A binding already exists for that permission level, remove it before setting a new one"
            ) from e

        if not role.members:
            return await ctx.send(f"{POSITIVE_CHECK} | Permission binding created!")

        view = Confirm(ctx.author)
        view.message = await ctx.send(
            f"{POSITIVE_CHECK} | Permission binding created! Re-calculate permissions of members with the role?",
            view=view,
        )
        await view.wait()
        if not view.value:
            return

        updated = await self.bot.db.query(
            """WITH updt AS (
                UPDATE necrobot.Permissions
                SET level=$1
                WHERE guild_id=$2 AND user_id = ANY($3) AND level < $1
                RETURNING user_id
            )
            SELECT array_agg(user_id) FROM updt;""",
            level,
            ctx.guild.id,
            [x.id for x in role.members],
            fetchval=True,
        )

        if updated is None:
            updated = 0
        else:
            updated = len(updated)

        await view.message.edit(content=f"{POSITIVE_CHECK} | Permissions of **{updated}** member(s) updated")

    @commands.command()
    @has_perms(4)
    async def promote(
        self,
        ctx: commands.Context[NecroBot],
        member: Annotated[discord.Member, MemberConverter],
    ):
        """Promote a member by one on the Necrobot hierarchy scale. Gaining access to additional commands.

        {usage}

        __Examples__
        `{pre}promote NecroBot` - promote necrobot by one level
        """
        current = await self.bot.db.get_permission(member.id, ctx.guild.id)
        await ctx.invoke(self.bot.get_command("permissions"), user=member, level=current + 1)

    @commands.command()
    @has_perms(4)
    async def demote(
        self,
        ctx: commands.Context[NecroBot],
        member: Annotated[discord.Member, MemberConverter],
    ):
        """Demote a member by one on the Necrobot hierarchy scale. Losing access to certain commands.

        {usage}

        __Examples__
        `{pre}demote NecroBot` - demote necrobot by one level
        """
        current = await self.bot.db.get_permission(member.id, ctx.guild.id)
        await ctx.invoke(self.bot.get_command("permissions"), user=member, level=current - 1)

    @commands.group(invoke_without_command=True)
    @has_perms(4)
    async def automod(
        self,
        ctx: commands.Context[NecroBot],
        *mentions: Union[MemberConverter, discord.TextChannel, RoleConverter],
    ):
        """Used to manage the list of channels and user ignored by the bot's automoderation system. If no mentions are \
        given it will print out the list of ignored Users (**U**) and the list of ignored Channels (**C**). The automoderation \
        feature tracks the edits made by users to their own messages and the deleted messages, printing them in the server's automod \
        channel. If mentions are given then it will add any user/channel not already ignored and remove any user/channel already ignored. \

        The bot also uses the automod channel to inform you of moderation actions that take place around your server, invites used by users \
        joining and attempts at mute evasions.

        {usage}

        __Example__
        `{pre}automod` - prints the list of users/channels ignored by necrobot's automoderation feature
        `{pre}automod @Necro #general` - adds user Necro and channel general to list of users/channels ignored by the necrobot's automoderation
        `{pre}automod @NecroBot #general` - adds user Necrobot to the list of users ignored by the automoderation and removes channel #general
        from it (since we added it above)
        `{pre}automod @ARole` - adds role ARole to the list of roles ignored by automoderation
        """

        def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
            string = "\n- ".join(entries)
            embed = discord.Embed(
                title=f"Ignored by Automod ({view.page_string})",
                colour=self.bot.bot_color,
                description=f"Channels(**C**), Users(**U**) and Roles (**R**) ignored by auto moderation:\n- {string}",
            )

            embed.set_footer(**self.bot.bot_footer)
            return embed

        if not mentions:
            ignored = self.bot.guild_data[ctx.guild.id]["ignore-automod"]
            return await Paginator(10, self.get_all(ctx, ignored, embed_maker=embed_maker), ctx.author).start(
                ctx
            )

        to_add = []
        to_remove = []

        for x in mentions:
            if x.id in self.bot.guild_data[ctx.guild.id]["ignore-automod"]:
                to_remove.append(x)
            else:
                to_add.append(x)

        if to_add:
            string = ", ".join([f"**{x.name}**" for x in to_add])
            await self.bot.db.insert_automod_ignore(ctx.guild.id, *[x.id for x in to_add])
            await ctx.send(f"{POSITIVE_CHECK} | {string} will now be ignored")

        if to_remove:
            string = ", ".join([f"**{x.name}**" for x in to_remove])
            await self.bot.db.delete_automod_ignore(ctx.guild.id, *[x.id for x in to_remove])
            await ctx.send(f"{POSITIVE_CHECK} | {string} will no longer be ignored")

    @automod.command(name="channel")
    @has_perms(4)
    async def automod_channel(
        self, ctx: commands.Context[NecroBot], channel: Union[discord.TextChannel, str] = None
    ):
        """Sets the auto-moderation channel to [channel], [channel] argument should be a channel mention. All the \
        auto-moderation related messages will be sent there.

        {usage}

        __Example__
        `{pre}automod channel #channel` - set the auto-moderation messages to be sent to channel 'channel'
        `{pre}automod channel disable` - disables auto-moderation for the entire server
        `{pre}automod channel` - see what the auto-moderation channel is currently"""

        if isinstance(channel, discord.TextChannel):
            check_channel(channel)
            await self.bot.db.update_automod_channel(ctx.guild.id, channel.id)
            await ctx.send(
                f"{POSITIVE_CHECK} | Okay, all automoderation messages will be posted in {channel.mention} from now on."
            )
        elif str(channel).lower() == "disable":
            await self.bot.db.update_automod_channel(ctx.guild.id)
            await ctx.send(f"{POSITIVE_CHECK} | Auto-moderation **disabled**")
        else:
            channel = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
            await ctx.send(
                f"Automod channel is currently set to {channel.mention if channel else 'Disabled'}. Use `automod channel disable` to disable"
            )

    @commands.command()
    @has_perms(4)
    async def ignore(
        self,
        ctx: commands.Context[NecroBot],
        *mentions: Union[MemberConverter, discord.TextChannel, RoleConverter],
    ):
        """Used to manage the list of channels and user ignored by the bot's command system. If no mentions are \
        given it will print out the list of ignored Users (**U**) and the list of ignored Channels (**C**). Being ignored \
        by the command system means that user cannot use any of the bot commands on the server. If mentions are given then \
        it will add any user/channel not already ignored and remove any user/channel already ignored.

        {usage}

        __Example__
        `{pre}ignore` - prints the list of users/channels ignored by necrobot
        `{pre}ignore @Necro #general` - adds user Necro and channel general to list of users/channels ignored by the necrobot
        `{pre}ignore @NecroBot #general` - adds user Necrobot to the list of users ignored by the bot and removes channel #general \
        from it (since we added it above)
        `{pre}ignore @ARole` - adds role ARole to the list of roles ignored by the bot
        """

        if not mentions:
            ignored = self.bot.guild_data[ctx.guild.id]["ignore-command"]

            def embed_maker(view: Paginator, entries: List[Dict[str, Any]]):
                string = "\n- ".join(entries)
                embed = discord.Embed(
                    title=f"Ignored by command ({view.page_string})",
                    colour=self.bot.bot_color,
                    description=f"Channels(**C**), Users(**U**) and Roles (**R**) ignored by the bot:\n- {string}",
                )

                embed.set_footer(**self.bot.bot_footer)
                return embed

            return await Paginator(10, self.get_all(ctx, ignored, embed_maker=embed_maker), ctx.author).start(
                ctx
            )

        to_add = []
        to_remove = []

        mentions = set(mentions)
        for x in mentions:
            if (
                isinstance(x, discord.Member)
                and (await self.bot.db.compare_user_permission(ctx.author.id, ctx.guild.id, x.id)) < 1
            ):
                raise BotError(f"You don't have the permissions required to ignore {x.mention}")

            if x.id in self.bot.guild_data[ctx.guild.id]["ignore-command"]:
                to_remove.append(x)
            else:
                to_add.append(x)

        if to_add:
            string = ", ".join([f"**{x.name}**" for x in to_add])
            await self.bot.db.insert_command_ignore(ctx.guild.id, *[x.id for x in to_add])
            await ctx.send(f"{POSITIVE_CHECK} | {string} will now be ignored")

        if to_remove:
            string = ", ".join([f"**{x.name}**" for x in to_remove])
            await self.bot.db.delete_command_ignore(ctx.guild.id, *[x.id for x in to_remove])
            await ctx.send(f"{POSITIVE_CHECK} | {string} will no longer be ignored")

    @commands.command(aliases=["setting"])
    @has_perms(4)
    async def settings(self, ctx: commands.Context[NecroBot]):
        """Creates a rich embed of the server settings

        {usage}"""
        server = self.bot.guild_data[ctx.guild.id]
        embed = discord.Embed(
            title="Server Settings",
            colour=self.bot.bot_color,
            description="Info on the NecroBot settings for this server",
        )
        embed.add_field(
            name="Welcome Channel",
            value=self.bot.get_channel(server["welcome-channel"]).mention
            if server["welcome-channel"]
            else "Disabled",
        )
        embed.add_field(
            name="Welcome Message",
            value=server["welcome"][:1024] if server["welcome"] else "None",
            inline=False,
        )
        embed.add_field(
            name="Farewell Message",
            value=server["goodbye"][:1024] if server["goodbye"] else "None",
            inline=False,
        )
        embed.add_field(
            name="Mute Role",
            value=ctx.guild.get_role(server["mute"]).mention if server["mute"] else "Disabled",
        )
        embed.add_field(name="Prefix", value=f'`{server["prefix"]}`' if server["prefix"] else "`n!`")

        embed.add_field(name="PM Warnings", value=server["pm-warning"], inline=False)
        embed.add_field(
            name="Auto Role",
            value=ctx.guild.get_role(server["auto-role"]).mention if server["auto-role"] else "Disabled",
        )
        embed.add_field(
            name="Auto Role Time Limit",
            value=server["auto-role-timer"] if server["auto-role-timer"] else "Permanent",
        )
        embed.add_field(
            name="Automod Channel",
            value=self.bot.get_channel(server["automod"]).mention if server["automod"] else "Disabled",
            inline=False,
        )
        embed.add_field(
            name="Starboard",
            value=self.bot.get_channel(server["starboard-channel"]).mention
            if server["starboard-channel"]
            else "Disabled",
        )
        embed.add_field(name="Starboard Limit", value=server["starboard-limit"])

        embed.set_footer(**self.bot.bot_footer)

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @has_perms(4)
    async def welcome(self, ctx: commands.Context[NecroBot], *, message: str = ""):
        """Sets the message that will be sent to the designated channel everytime a member joins the server. You \
        can use special keywords to replace certain words by stuff like the name of the member or a mention.
        List of keywords:
        `{{mention}}` - mentions the member
        `{{member}}` - name and discriminator of the member
        `{{name}}` - name of the member
        `{{server}}` - name of the server
        `{{id}}` - id of the member that joined

        {usage}

        __Example__
        `{pre}welcome Hello {{member}} :wave:` - sets the welcome message to be 'Hello Necrobot#1231 :wave:'.
        `{pre}welcome hey there {{mention}}, welcome to {{server}}` - set the welcome message to 'hey there @NecroBot, welcome \
        to NecroBot Support Server'
        `{pre}welcome` - disable server welcome message
        """
        if message == "":
            await ctx.send(f"{POSITIVE_CHECK} | Welcome message reset and disabled")
        else:
            try:
                test = message.format(
                    **build_format_dict(member=ctx.author, guild=ctx.guild, channel=ctx.channel)
                )
                await ctx.send(f"{POSITIVE_CHECK} | Your server's welcome message will be: \n{test}")
            except KeyError as e:
                raise BotError(
                    f"{e.args[0]} is not a valid argument. Check the help guide to see what you can use the command with."
                ) from e

        await self.bot.db.update_welcome_message(ctx.guild.id, message)

    @commands.group(invoke_without_command=True)
    @has_perms(4)
    async def farewell(self, ctx: commands.Context[NecroBot], *, message: str = ""):
        """Sets the message that will be sent to the designated channel everytime a member leaves the server. You \
        can use special keywords to replace certain words by stuff like the name of the member or a mention.
        List of keywords:
        `{{mention}}` - mentions the member
        `{{member}}` - name and discriminator of the member
        `{{name}}` - name of the member
        `{{server}}` - name of the server
        `{{id}}` - id of the member that left

        {usage}

        __Example__
        `{pre}farewell Hello {{member}} :wave:` - sets the farewell message to be 'Hello Necrobot#1231 :wave:'.
        `{pre}farewell hey there {{mention}}, we'll miss you on {{server}}` - set the farewell message to 'hey \
        there @NecroBot, we'll miss you on NecroBot Support Server'
        """
        if message == "":
            await ctx.send(f"{POSITIVE_CHECK} | Farewell message reset and disabled")
        else:
            try:
                test = message.format(
                    **build_format_dict(member=ctx.author, guild=ctx.guild, channel=ctx.channel)
                )
                await ctx.send(f"{POSITIVE_CHECK} | Your server's farewell message will be: \n{test}")
            except KeyError as e:
                raise BotError(
                    f"{e.args[0]} is not a valid argument. Check the help guide to see what you can use the command with."
                ) from e

        await self.bot.db.update_farewell_message(ctx.guild.id, message)

    async def channel_set(self, ctx: commands.Context[NecroBot], channel):
        if not channel:
            await self.bot.db.update_greeting_channel(ctx.guild.id)
            await ctx.send(f"{POSITIVE_CHECK} | Welcome/Farewell messages **disabled**")
        else:
            check_channel(channel)
            await self.bot.db.update_greeting_channel(ctx.guild.id, channel.id)
            await ctx.send(
                f"{POSITIVE_CHECK} | Users will get their welcome/farewell message in {channel.mention} from now on."
            )

    @welcome.command(name="channel")
    @has_perms(4)
    async def welcome_channel(
        self,
        ctx: commands.Context[NecroBot],
        channel: Annotated[discord.TextChannel, WritableChannelConverter] = 0,
    ):
        """Sets the welcome channel to [channel], the [channel] argument should be a channel mention/name/id. The welcome \
        message for users will be sent there. Can be called with either farewell or welcome, regardless both will use \
        the same channel, calling the command with both parent commands but different channel will not make \
        messages send to two channels.

        {usage}

        __Example__
        `{pre}welcome channel #channel` - set the welcome messages to be sent to 'channel'
        `{pre}welcome channel` - disables welcome messages"""

        await self.channel_set(ctx, channel)

    @farewell.command(name="channel")
    @has_perms(4)
    async def farewell_channel(
        self,
        ctx: commands.Context[NecroBot],
        channel: Annotated[discord.TextChannel, WritableChannelConverter] = 0,
    ):
        """Sets the welcome channel to [channel], the [channel] argument should be a channel mention. The welcome \
        message for users will be sent there. Can be called with either farewell or welcome, regardless both will use \
        the same channel, calling the command with both parent commands but different channel will not make \
        messages send to two channels.

        {usage}

        __Example__
        `{pre}farewell channel #channel` - set the welcome messages to be sent to 'channel'
        `{pre}farewell channel` - disables welcome messages"""

        await self.channel_set(ctx, channel)

    @commands.command(name="prefix")
    @has_perms(4)
    async def prefix(self, ctx: commands.Context[NecroBot], *, prefix: str = ""):
        r"""Sets the bot to only respond to the given prefix. If no prefix is given it will reset it to NecroBot's default \
        list of prefixes: `n!`, `N!` or `@NecroBot `. The prefix can't be longer than 15 characters.

        If you want your prefix to have a whitespace between the prefix and the command then end it with \w

        {usage}

        __Example__
        `{pre}prefix bob! potato` - sets the prefix to be `bob! potato ` so a command like `{pre}cat` will now be \
        summoned like this `bob! potato cat`
        `{pre}prefix` - resets the prefix to NecroBot's default list"""
        prefix = prefix.replace(r"\w", " ")

        if len(prefix) > 15:
            raise BotError(f"Prefix can't be more than 15 characters. {len(prefix)}/15")

        await self.bot.db.update_prefix(ctx.guild.id, prefix)

        if prefix == "":
            await ctx.send(f"{POSITIVE_CHECK} | Custom prefix reset")
        else:
            await ctx.send(f"{POSITIVE_CHECK} | Server prefix is now **{prefix}**")

    @commands.command(name="auto-role")
    @has_perms(4)
    async def auto_role(
        self,
        ctx: commands.Context[NecroBot],
        role: Annotated[discord.Role, RoleConverter] = 0,
        time: TimeConverter = 0,
    ):
        """Sets the auto-role for this server to the given role. Auto-role will assign the role to the member when they join. \
        The following times can be used: days (d), hours (h), minutes (m), seconds (s).

        {usage}

        __Example__
        `{pre}auto-role Newcomer 10m` - gives the role "Newcomer" to users to arrive on the server for 10 minutes
        `{pre}auto-role Newcomer 2d10m` - same but the roles stays for 2 days and 10 minutes
        `{pre}auto-role Newcomer 4h45m56s` - same but the role stays for 4 hours, 45 minutes and 56 seconds
        `{pre}auto-role Newcomer` - gives the role "Newcomer" with no timer to users who join the server.
        `{pre}auto-role` - resets and disables the autorole system."""

        if not role:
            await ctx.send(f"{POSITIVE_CHECK} | Auto-Role disabled")
            await self.bot.db.update_auto_role(ctx.guild.id, 0, time)
        else:
            if not isinstance(time, int):
                raise BotError("Please specify a valid time format")

            time_string = f"for **{time}** seconds" if time else "permanently"
            await ctx.send(
                f"{POSITIVE_CHECK} | Joining members will now automatically be assigned the role **{role.name}** {time_string}"
            )
            await self.bot.db.update_auto_role(ctx.guild.id, role.id, time)

    @commands.group(invoke_without_command=True, aliases=["broadcasts"])
    @has_perms(4)
    async def broadcast(self, ctx: commands.Context[NecroBot]):
        """See all the broadcasts currently set up on the server. Root command for setting up other broadcasts

        {usage}

        __Examples__
        `{pre}broadcast` - see all broadcast currently set up
        `{pre}broadcast add #channel` - start the process of adding a new broadcast by defining the channel it will be posted in
        `{pre}broadcast delete 3` - delete a broadcast based on the id
        `{pre}broadcast edit channel 2 #another-channel` - change the channel that broadcast 2 is broadcasting to
        """

        def embed_maker(view: Paginator, entry):
            embed = discord.Embed(
                title=f"Broadcast ({view.page_string})",
                description=entry[5],
                colour=self.bot.bot_color,
            )

            embed.add_field(name="Channel", value=ctx.guild.get_channel(entry[2]).mention)
            embed.add_field(name="Start Time", value=f"{entry[3]}h")
            embed.add_field(name="Interval", value=f"Every {entry[4]} hours")
            embed.add_field(name="ID", value=entry[0])
            embed.add_field(name="Enabled?", value="Yes" if entry[6] else "No")

            embed.set_footer(**self.bot.bot_footer)
            return embed

        broadcasts = await self.bot.db.query(
            "SELECT * FROM necrobot.Broadcasts WHERE guild_id = $1", ctx.guild.id
        )

        await Paginator(1, broadcasts, ctx.author, embed_maker=embed_maker).start(ctx)

    async def broadcast_editor(
        self,
        defaults: Dict[str, EmbedDefaultConverter],
        channel: discord.TextChannel,
        ctx: commands.Context[NecroBot],
    ) -> MultiInputEmbedView:
        async def embed_maker(values):
            embed = discord.Embed(
                title="New Broadcast!",
                description=await transform_mentions(ctx, values["message"]),
                colour=self.bot.bot_color,
            )

            embed.add_field(name="Channel", value=channel.mention)
            embed.add_field(name="Start Time", value=f"{values['start']}h (Current hour: {self.bot.counter})")
            embed.add_field(name="Interval", value=f"Every {values['interval']} hours")

            embed.set_footer(**self.bot.bot_footer)
            return embed

        view = MultiInputEmbedView(embed_maker, defaults, "Broadcast Edit", ctx.author)
        view.message = await ctx.send(
            f"You can submit the edit form anytime. Missing field will only be checked on confirmation. Current bot hour is {self.bot.counter}\n- interval should be between 1 and 24\n- start should be between 0 and 23\n",
            embed=await view.generate_embed(),
            view=view,
        )

        await view.wait()
        return view

    @broadcast.command(name="add")
    @has_perms(4)
    async def broadcast_add(
        self,
        ctx: commands.Context[NecroBot],
        channel: Annotated[discord.TextChannel, WritableChannelConverter],
    ):
        """Start the process for adding a new broadcast.

        **Disclaimer**: The start parameter does not actually dictate when the first broadcast will occur, it simply insures \
        that the broadcast happens on the hour specified and uses it as a benchmark to determine whether the broadcast should \
        happen at every other hour. Broadcasts will small intervals are likely to be posted before the "start" time. \

        {usage}

        __Examples__
        `{pre}broadcast add #lounge` - start the process of adding a broadcast to lounge
        """
        defaults = {
            "message": EmbedStringConverter(style=discord.TextStyle.paragraph),
            "start": EmbedRangeConverter(min=0, max=23),
            "interval": EmbedRangeConverter(default="1", min=1, max=24),
        }
        view = await self.broadcast_editor(defaults, channel, ctx)
        if not view.value:
            return

        values = view.convert_values()

        broadcast_id = await self.bot.db.query(
            "INSERT INTO necrobot.Broadcasts(guild_id, channel_id, start_time, interval, message) VALUES ($1, $2, $3, $4, $5) RETURNING broadcast_id",
            ctx.guild.id,
            channel.id,
            int(values["start"]),
            int(values["interval"]),
            await transform_mentions(ctx, values["message"]),
            fetchval=True,
        )

        await ctx.send(
            f"{POSITIVE_CHECK} | Your broadcast is ready (ID: **{broadcast_id}**) and will start as soon as possible!"
        )

    @broadcast.command(name="edit")
    @has_perms(4)
    async def broadcast_edit(
        self,
        ctx: commands.Context[NecroBot],
        broadcast_id: int,
    ):
        """Edit a broadcast's settings

        {usage}

        __Examples__
        `{pre}broadcast edit 2` - Edit the settings of broadcast with ID 2
        """
        query = await self.bot.db.query(
            "SELECT * FROM necrobot.Broadcasts WHERE broadcast_id = $1 AND guild_id = $2",
            broadcast_id,
            ctx.guild.id,
        )
        if not query:
            raise BotError("No broadcast found with that ID")

        defaults = {
            "message": EmbedStringConverter(
                default=await commands.clean_content(use_nicknames=False, fix_channel_mentions=True).convert(
                    ctx, str(query[0]["message"])
                ),
                style=discord.TextStyle.paragraph,
            ),
            "start": EmbedRangeConverter(default=str(query[0]["start_time"]), min=0, max=23),
            "interval": EmbedRangeConverter(default=str(query[0]["interval"]), min=1, max=24),
        }
        view = await self.broadcast_editor(defaults, ctx.guild.get_channel(query[0]["channel_id"]), ctx)
        if not view.value:
            return

        values = view.convert_values()

        broadcast_id = await self.bot.db.query(
            "UPDATE necrobot.Broadcasts SET start_time = $3, interval = $4, message = $5 WHERE broadcast_id = $1 AND guild_id = $2",
            broadcast_id,
            ctx.guild.id,
            int(values["start"]),
            int(values["interval"]),
            await transform_mentions(ctx, values["message"]),
        )

        await ctx.send(f"{POSITIVE_CHECK} | Broadcast edited!")

    @broadcast.command(name="delete")
    @has_perms(4)
    async def broadcast_del(self, ctx: commands.Context[NecroBot], broadcast_id: int):
        """Delete a broadcast permanently

        {usage}
        """
        value = await self.bot.db.query(
            "DELETE FROM necrobot.Broadcasts WHERE broadcast_id = $1 AND guild_id = $2 RETURNING broadcast_id",
            broadcast_id,
            ctx.guild.id,
            fetchval=True,
        )

        if value:
            await ctx.send(f"{POSITIVE_CHECK} | Deleted broadcast")
        else:
            raise BotError("No broadcast found with that ID")

    @broadcast.command(name="toggle")
    @has_perms(4)
    async def broadcast_toggle(self, ctx: commands.Context[NecroBot], broadcast_id: int):
        """Toggle a broadcast on/off. Turning a broadcast off retains the data but stops the message \
        from broadcasting.

        {usage}

        """
        changed = await self.bot.db.query(
            "UPDATE necrobot.Broadcasts SET enabled=(NOT enabled) WHERE broadcast_id = $1 AND guild_id = $2 RETURNING enabled",
            broadcast_id,
            ctx.guild.id,
            fetchval=True,
        )

        if changed is None:
            raise BotError("No broadcast found with that ID")

        if changed:
            await ctx.send(f"{POSITIVE_CHECK} | Broadcast enabled")
        else:
            await ctx.send(f"{POSITIVE_CHECK} | Broadcast disabled")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def giveme(
        self,
        ctx: commands.Context[NecroBot],
        *,
        role: Annotated[discord.Role, RoleConverter] = None,
    ):
        """Gives the user the role if it is part of this Server's list of self assignable roles. If the user already \
        has the role it will remove it. **Roles names are case sensitive** If no role name is given then it will list \
        the self-assignable roles for the server

        {usage}

        __Example__
        `{pre}giveme Good` - gives or remove the role 'Good' to the user if it is in the list of self assignable roles"""

        if role is None:

            def embed_maker(view: GivemePaginator, entries: List[discord.Role]):
                embed = discord.Embed(
                    title=f"Self Assignable Roles ({view.page_string})",
                    description="\n".join([f"- {role.mention} ({len(role.members)})" for role in entries]),
                    colour=self.bot.bot_color,
                )

                embed.set_footer(**self.bot.bot_footer)
                return embed

            roles = [
                ctx.guild.get_role(role_id)
                for role_id in self.bot.guild_data[ctx.guild.id]["self-roles"]
                if ctx.guild.get_role(role_id) is not None
            ]
            return await GivemePaginator(20, roles, ctx.author, embed_maker=embed_maker).start(ctx)

        if role.id in self.bot.guild_data[ctx.guild.id]["self-roles"]:
            if role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                await ctx.send(f"{POSITIVE_CHECK} | Role **{role.name}** added.")
            else:
                await ctx.author.remove_roles(role)
                await ctx.send(f"{POSITIVE_CHECK} | Role **{role.name}** removed.")

        else:
            raise BotError("Role not self assignable")

    @giveme.command(name="add")
    @has_perms(4)
    async def giveme_add(
        self,
        ctx: commands.Context[NecroBot],
        *,
        role: Annotated[discord.Role, RoleConverter],
    ):
        """Adds [role] to the list of the server's self assignable roles.

        {usage}

        __Example__
        `{pre}giveme add Good` - adds the role 'Good' to the list of self assignable roles"""
        if role.managed:
            raise BotError("Cannot add a managed role")

        if role.id in self.bot.guild_data[ctx.guild.id]["self-roles"]:
            raise BotError("Role already in list of self assignable roles")

        await self.bot.db.insert_self_roles(ctx.guild.id, role.id)
        await ctx.send(f"{POSITIVE_CHECK} | Added role **{role.name}** to list of self assignable roles.")

    @giveme.command(name="delete")
    @has_perms(4)
    async def giveme_delete(
        self,
        ctx: commands.Context[NecroBot],
        *,
        role: Annotated[discord.Role, RoleConverter],
    ):
        """Removes [role] from the list of the server's self assignable roles.

        {usage}

        __Example__
        `{pre}giveme delete Good` - removes the role 'Good' from the list of self assignable roles"""
        if role.id not in self.bot.guild_data[ctx.guild.id]["self-roles"]:
            raise BotError("Role not in self assignable list")

        await self.bot.db.delete_self_roles(ctx.guild.id, role.id)
        await ctx.send(f"{POSITIVE_CHECK} | Role **{role.name}** removed from self assignable roles")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @has_perms(4)
    async def starboard(
        self,
        ctx: commands.Context[NecroBot],
        channel: Annotated[discord.TextChannel, WritableChannelConverter] = None,
    ):
        """Sets a channel for the starboard messages, required in order for starboard to be enabled. Call the command \
        without a channel to disable starboard.

        {usage}

        __Examples__
        `{pre}starboard #a-channel` - sets the starboard channel to #a-channel, all starred messages will be sent to
        there
        `{pre}starboard` - disables starboard"""
        if channel is None:
            await self.bot.db.update_starboard_channel(ctx.guild.id)
            await ctx.send(f"{POSITIVE_CHECK} | Starboard disabled.")
        else:
            check_channel(channel)
            await self.bot.db.update_starboard_channel(ctx.guild.id, channel.id)
            await ctx.send(f"{POSITIVE_CHECK} | Starred messages will now be sent to {channel.mention}")

    @starboard.command(name="limit")
    @has_perms(4)
    async def starboard_limit(self, ctx: commands.Context[NecroBot], limit: int):
        """Sets the amount of stars required to the given intenger. Must be more than 0.

        {usage}

        __Examples__
        `{pre}starboard limit 4` - set the required amount of stars on a message to 4, once a message hits 4 :star: they \
        will be posted if there is a starboard channel set."""
        if limit < 1:
            raise BotError("Limit must be at least one")

        await self.bot.db.update_starboard_limit(ctx.guild.id, limit)
        await ctx.send(
            f"{POSITIVE_CHECK} | Starred messages will now be posted on the starboard once they hit **{limit}** stars"
        )

    @starboard.command(name="force")
    @has_perms(3)
    async def starboard_force(self, ctx: commands.Context[NecroBot], message_id: int):
        """Allows to manually star a message that either has failed to be sent to starboard or doesn't \
        have the amount of stars required. This functionality was moved to a context menu and the command \
        will soon be removed.

        {usage}

        __EXamples__
        `{pre}starboard force 427227137511129098` - gets the message by id and stars it.
        """
        await ctx.send("This functionality was moved to a context menu and the command will soon be removed.")

        if not self.bot.guild_data[ctx.guild.id]["starboard-channel"]:
            raise BotError("Please set a starboard first")

        try:
            message = await ctx.channel.fetch_message(message_id)
        except Exception as e:
            raise BotError("Message not found, make sure you are in the channel with the message.") from e

        await self.bot.meta.star_message(message)
        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(
                title="Message Force Starred",
                description=f"{ctx.author.mention} force starred a message",
                colour=self.bot.bot_color,
            )
            embed.add_field(name="Link", value=message.jump_url)
            embed.set_footer(**self.bot.bot_footer)
            await automod.send(embed=embed)

    @commands.command()
    @has_perms(3)
    async def poll(
        self,
        ctx: commands.Context[NecroBot],
        channel: Annotated[discord.TextChannel, WritableChannelConverter],
    ):
        """Start the creation process for a poll in a given channel.

        {usage}

        __Examples__
        `{pre}poll #general` - Start the creation process for a poll to be sent in #general
        """
        view = PollEditorView(channel, self.bot, ctx.author)
        await ctx.send(f"Let's start making your poll in {channel.mention}", view=view)


async def setup(bot: NecroBot):
    await bot.add_cog(Server(bot))
