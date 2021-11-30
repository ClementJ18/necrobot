import discord
from discord.ext import commands

from rings.utils.utils import BotError, react_menu, format_dt
from rings.utils.converters import TimeConverter, MemberConverter, RoleConverter, RangeConverter
from rings.utils.checks import has_perms, requires_mute_role

import asyncio
import datetime
from typing import Union

class Moderation(commands.Cog):
    """All of the tools moderators can use from the most basic such as `nick` to the most complex like `purge`. 
    All you need to keep your server clean and tidy"""
    def __init__(self, bot):
        self.bot = bot
        
    #######################################################################
    ## Cog Functions
    #######################################################################

    def cog_check(self, ctx):
        if ctx.guild:
            return True

        raise commands.CheckFailure("This command cannot be used in private messages.")
       
    #######################################################################
    ## Functions
    #######################################################################   
     
    async def mute_task(self, ctx, user, role, time):
        await asyncio.sleep(time)
        
        if user.id in self.bot.guild_data[user.guild.id]["mutes"]:
            self.bot.guild_data[user.guild.id]["mutes"].remove(user.id)
        
        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if role in user.roles and ctx.guild.get_member(user.id) is not None:
            await user.remove_roles(role)

            if automod is not None:
                embed = discord.Embed(title="User Unmuted", description=f"**{user.display_name}** has been automatically unmuted", colour=self.bot.bot_color)
                embed.set_footer(**self.bot.bot_footer)
                await automod.send(embed=embed)
    
    #######################################################################
    ## Commands
    #######################################################################

    @commands.command()
    @has_perms(3)
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx, user : Union[MemberConverter, int], reason = None):
        """Ban a user, sending them a message and add the message as a reason

        {usage}

        __Examples__
        `{pre}ban NecroBot` - ban Necrobot
        `{pre}ban Necrobot good bot` - ban Necrobot and send it a message"""
        
        if isinstance(user, discord.Member) and reason is not None:
            try:
                await user.send(f"__Banned from {ctx.guild.name}__\nReason: {reason}")
                await ctx.message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
            except discord.Forbidden:
                await ctx.message.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")

        if isinstance(user, int):
            user = discord.Object(id=user)
            user.name = "Hackbanned"

        if reason is not None:
            await ctx.guild.ban(user, reason=reason)
        else:
            await ctx.guild.ban(user)

        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="User Banned", description=f"{user.name} ({user.id}) banned by {ctx.author.mention}", colour=self.bot.bot_color)
            embed.add_field(name="Reason", value=reason)

            embed.set_footer(**self.bot.bot_footer)

            await automod.send(embed=embed)


    
    @commands.command()
    @has_perms(1)
    @commands.bot_has_permissions(manage_nicknames=True)
    async def rename(self, ctx, user : MemberConverter, *, nickname=None):
        """ Nicknames a user, use to clean up offensive or vulgar names or just to prank your friends. Will return 
        an error message if the user cannot be renamed due to permission issues.
        
        {usage}
        
        __Example__
        `{pre}nick @NecroBot Lord of All Bots` - renames NecroBot to 'Lord of All Bots'
        `{pre}nick @NecroBot` - will reset NecroBot's nickname"""
        if await self.bot.db.compare_user_permission(ctx.author.id, ctx.guild.id, user.id) < 1:
            raise BotError("You do not have the required NecroBot permissions to rename this user.")

        if not nickname:
            msg = f":white_check_mark: | User **{user.display_name}**'s nickname reset"
        else:
            msg = f":white_check_mark: | User **{user.display_name}** renamed to **{nickname}**"

        old_name = user.display_name

        await user.edit(nick=nickname)
        await ctx.send(msg)

        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="User Renamed", description=f"{user.mention} renamed by {ctx.author.mention}", colour=self.bot.bot_color)
            embed.set_footer(**self.bot.bot_footer)
            embed.add_field(name="Old Name", value=old_name)
            embed.add_field(name="New Name", value=user.display_name)

            await automod.send(embed=embed)

    @commands.group(invoke_without_command = True)
    @has_perms(2)
    @requires_mute_role()
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx, user : MemberConverter, time : TimeConverter = None):
        """Blocks the user from writing in channels by giving it the server's mute role. Make sure an admin has set a 
        mute role using `{pre}mute role`. The user can either be muted for the given amount of seconds or indefinitely 
        if no amount is given. The following times can be used: days (d), hours (h), minutes (m), seconds (s).
        
        {usage}

        __Example__
        `{pre}mute @NecroBot` - mute NecroBot until a user with the proper permission level does `{pre}unmute @NecroBot`
        `{pre}mute @NecroBot 30s` - mutes NecroBot for 30 seconds or until a user with the proper permission level does
        `{pre}mute @NecroBot 2m` - mutes NecroBot for 2 minutes
        `{pre}mute @NecroBot 4d2h45m` - mutes NecroBot for 4 days, 2 hours and 45 minutes"""
        if await self.bot.db.compare_user_permission(ctx.author.id, ctx.guild.id, user.id) < 1:
            raise BotError("You do not have the required NecroBot permissions to mute this user.")

        role = discord.utils.get(ctx.guild.roles, id=self.bot.guild_data[ctx.guild.id]["mute"])
        if role not in user.roles:
            await user.add_roles(role)
            await ctx.send(f":white_check_mark: | User **{user.display_name}** has been muted")
        else:
            raise BotError(f"User **{user.display_name}** is already muted")

        if time:
            self.bot.loop.create_task(self.mute_task(ctx, user, role, time))

        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="User Muted", description=f"{user.mention} muted by {ctx.author.mention}", colour=self.bot.bot_color)
            embed.set_footer(**self.bot.bot_footer)
            embed.add_field(name="Unmute Time", value=format_dt(datetime.datetime.now() + datetime.timedelta(seconds=time)) if time else "Permanently")
            await automod.send(embed=embed)

    @mute.group(name="role", invoke_without_command=True)
    @has_perms(4)
    async def mute_role(self, ctx, *, role : RoleConverter = 0):
        """Sets the mute role for this server to [role], this is used for the `mute` command, it is the role assigned by 
        the command to the user. Make sure to spell the role correctly, the role name is case sensitive. It is up to the server 
        authorities to set up the proper permissions for the chosen mute role. Once the role is set up it can be renamed and 
        edited as seen needed, NecroBot keeps the id saved. Unexpect behavior can happen if multiple roles have the same name when
        setting the role.
         
        {usage}
        
        __Example__
        `{pre}mute role Token Mute Role` - set the mute role to be the role named 'Token Mute Role'
        `{pre}mute role` - resets the mute role and disables the `mute` command.
        there is already a mute role this updates all the channels without permissions for it to disallow sending
        messages and connection"""
        if not role:
            await self.bot.db.update_mute_role(ctx.guild.id)
            await ctx.send(":white_check_mark: | Reset mute role")
        else:
            await self.bot.db.update_mute_role(ctx.guild.id, role.id)
            await ctx.send(f":white_check_mark: | Okay, the mute role for your server will be {role.mention}")

            
    @mute_role.command(name="create")
    @has_perms(4)
    @commands.bot_has_permissions(manage_roles=True, manage_channels=True)
    async def mute_role_create(self, ctx, *, name : str = None):
        """Creates the mute role for you if not already set and updates the channels where there are no overwrite
        already set for the mute role. This means any channel with overwrites already set will be skipped over.
        
        {usage}
        
        __Examples__
        `{pre}mute role create` - create the mute role with default name "Muted"
        `{pre}mute role create Timeout` - create the mute role with name "Timeout"
        """
        if not self.bot.guild_data[ctx.guild.id]["mute"]:
            role = await ctx.guild.create_role(
                name=name if name is not None else "Muted",
                permissions=discord.Permissions(permissions=0)
            )
            await self.bot.db.update_mute_role(ctx.guild.id, role.id)
            await ctx.send(f":white_check_mark: | Created mute role called {role.mention}")
        else:
            if name is not None:
                raise BotError("There is already a mute role set up, if you want to set up a new one please first reset the mute role.")
            
            role = ctx.guild.get_role(self.bot.guild_data[ctx.guild.id]["mute"])
            
        denied_perms = discord.PermissionOverwrite(
            add_reactions=False, 
            send_messages=False, 
            speak=False, 
            stream=False
        )
        for channel in ctx.guild.channels:
            overwrites = channel.overwrites_for(role)
            if overwrites.is_empty():
                try:
                    await channel.edit(overwrites={role : denied_perms}) 
                except discord.Forbidden:
                    pass  
                
        await ctx.send(f":white_check_mark: | Updated permissions for all channels where {role.mention} was not already present where I had permission.")
        
    @commands.command()
    @has_perms(2)
    @requires_mute_role()
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx, user : MemberConverter):
        """Unmutes a user by removing the mute role, allowing them once again to write in text channels. 
        
        {usage}

        __Example__
        `{pre}unmute @NecroBot` - unmutes NecroBot if he is muted"""
        if not self.bot.guild_data[ctx.guild.id]["mute"]:
            await ctx.send(":negative_squared_cross_mark: | Please set up the mute role with `n!mute role [rolename]` first.")
            return
            
        role = discord.utils.get(ctx.guild.roles, id=self.bot.guild_data[ctx.guild.id]["mute"])
        if role in user.roles:
            await user.remove_roles(role)
            await ctx.send(f":white_check_mark: | User **{user.display_name}** has been unmuted")
        else:
            await ctx.send(f":negative_squared_cross_mark: | User **{user.display_name}** is not muted", delete_after=5)

        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="User Unmuted", description=f"{user.mention} unmuted by {ctx.author.mention}", colour=self.bot.bot_color)
            embed.set_footer(**self.bot.bot_footer)
            await automod.send(embed=embed)
    
    @commands.group(invoke_without_command = True)
    @has_perms(1)
    async def warn(self, ctx, user : MemberConverter, *, message : str):
        """Adds the given message as a warning to the user's NecroBot profile
        
        {usage}
        
        __Example__
        `{pre}warn @NecroBot For being the best bot` - will add the warning 'For being the best bot' to 
        Necrobot's warning list and pm the warning message to him"""
        if await self.bot.db.compare_user_permission(ctx.author.id, ctx.guild.id, user.id) < 1:
            raise BotError("You do not have the required NecroBot permissions to warn this user.")

        warning_id = await self.bot.db.insert_warning(user.id, ctx.author.id, ctx.guild.id, message)
        await ctx.send(f":white_check_mark: | Warning added to warning list of user **{user.display_name}** with ID `{warning_id}`")
        
        if self.bot.guild_data[ctx.guild.id]["pm-warning"]:
            try:
                await user.send(f"You have been warned on {ctx.guild.name}, the warning is: \n {message}")
            except discord.Forbidden:
                pass

        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="User Warned", description=f"{user.mention} warned by {ctx.author.mention}", colour=self.bot.bot_color)
            embed.set_footer(**self.bot.bot_footer)
            embed.add_field(name="ID", value=warning_id)
            await automod.send(embed=embed)

    @warn.command(name="delete")
    @has_perms(3)
    async def warn_delete(self, ctx, warning_id : int):
        """Removes the warning from the user's NecroBot system based on the given warning id. 
        
        {usage}
        
        __Example__
        `{pre}warn delete @NecroBot 1` - delete the warning with id 1 of NecroBot's warning list"""
        
        deleted = await self.bot.db.delete_warning(warning_id, ctx.guild.id)
        if not deleted:
            raise BotError("Warning with that ID not found")
           
        user = ctx.guild.get_member(deleted) 
        await ctx.send(f":white_check_mark: | Warning `{warning_id}` removed from warning list of user **{user.display_name if user else 'User Left'}**")


        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="User Warning Deleted", description=f"{ctx.author.mention} deleted {warning_id}", colour=self.bot.bot_color)
            embed.set_footer(**self.bot.bot_footer)
            await automod.send(embed=embed)

    @warn.command(name="list")
    async def warn_list(self, ctx, user : MemberConverter = None):
        """List a user's warnings
        
        {usage}
        
        __Examples__
        `{pre}warn list Necrobot` - get a list of warnings for Necrobot
        `{pre}warn list` - get a list of your own warnings
        """
        if user is None:
            user = ctx.author
            
        warnings = await self.bot.db.query(
            "SELECT * FROM necrobot.Warnings WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id, user.id    
        )
        
        def embed_maker(index, entries):            
            embed = discord.Embed(
                title=f"Warnings ({index[0]}/{index[1]})", 
                colour=self.bot.bot_color, 
                description=f"List of warnings for {user.display_name}"
            )
            
            embed.set_footer(**self.bot.bot_footer)
            
            for entry in entries:
                embed.add_field(name=entry["warn_id"], value=entry["warning_content"][:1000], inline=False)
                
            return embed
            
        await react_menu(ctx, warnings, 5, embed_maker)
                
    @warn.command(name="get")
    async def warn_get(self, ctx, warn_id : int):
        """Get the information for a specific warning
        
        {usage}
        
        __Examples__
        `{pre}warn get 4` - get warning with id 4
        """
        warning = await self.bot.db.query(
            "SELECT * FROM necrobot.Warnings WHERE warn_id = $1 AND guild_id = $2",
            warn_id, ctx.guild.id    
        )
        
        if not warning:
            raise BotError("No warning from this server with that id")
            
        warning = warning[0]
            
        embed = discord.Embed(
            title=f"`{warn_id}`",
            colour=self.bot.bot_color, 
            description=warning["warning_content"]
        )
        
        issuer = self.bot.get_user(warning["issuer_id"])
        embed.add_field(name="Issuer", value=issuer.mention if not issuer is None else f"User has left ({warning['issuer_id']})")
        embed.add_field(name="Date Issued", value=warning["date_issued"].strftime("%Y-%m-%d %H:%M"))
        
        embed.set_footer(**self.bot.bot_footer)
        
        await ctx.send(embed=embed)
        
    @warn.command(name="pm")
    @has_perms(4)
    async def warn_pm(self, ctx, pm : bool):
        """Defines the setting on whether or not the user that is warned will be DM'd the warning. They
        will be PM'd if the setting is True. Disabled by default.
        
        {usage}
        
        __Examples__
        `{pre}warn pm True` - users will now be PM'd the warning
        `{pre}warn pm False` - users will not be PM'd the warning.
        """
        await self.bot.db.update_warning_setting(ctx.guild.id, pm)
        if pm:
            await ctx.send(":white_check_mark: | Users will be DM'd warnings")
        else:
            await ctx.send(":white_check_mark: | Users will not be DM's warnings.")

    @commands.command()
    @has_perms(4)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, number : int = RangeConverter(0, 400), check = "", extra : MemberConverter = ""):
        """Removes number of messages from the channel it is called in. That's all it does at the moment 
        but later checks will also be added to allow for more flexible/specific purging
        
        {usage}
        
        __Example__
        `{pre}purge 50` - purges the last 50 messages
        `{pre}purge 15 link` - purges all messages containing links from the previous 15 messages
        `{pre}purge 20 mention @Necro` - purges all messages sent by @Necro from the previous 20 messages
        `{pre}purge 35 bot` - purges all messages sent by the bot from the previous 35 messages"""
        number += 1
        check = check.lower()
        
        if check == "link":
            deleted = await ctx.channel.purge(limit=number, check=lambda m: "http" in m.content)
        elif check == "mention":
            deleted = await ctx.channel.purge(limit=number, check=lambda m: m.author == extra)
        elif check == "image":
            deleted = await ctx.channel.purge(limit=number, check=lambda m: m.attachments)
        elif check == "bot":
            deleted = await ctx.channel.purge(limit=number, check=lambda m: m.author == self.bot.user)
        else:
            deleted = await ctx.channel.purge(limit=number)

        await ctx.send(f":wastebasket: | **{len(deleted)-1}** messages purged.", delete_after=5)

        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="Purge", description=f"{ctx.author.mention} purged **{len(deleted)-1}** messages in {ctx.channel.mention}", colour=self.bot.bot_color)
            embed.set_footer(**self.bot.bot_footer)
            await automod.send(embed=embed)

    @commands.command()
    @has_perms(3)
    async def speak(self, ctx, channel : discord.TextChannel, *, message : str):
        """Send the given message to the channel mentioned by mention or name. Cannot send to other servers. 
        
        {usage}
        
        __Example__
        `{pre}speak #general Hello` - sends hello to the mentionned #general channel"""
        await channel.send(f":loudspeaker: | {message}")

        automod = ctx.guild.get_channel(self.bot.guild_data[ctx.guild.id]["automod"])
        if automod is not None:
            embed = discord.Embed(title="Moderator Proxied", description=f"{ctx.author.mention} spoke using the bot in {channel.mention}", colour=self.bot.bot_color)
            embed.set_footer(**self.bot.bot_footer)
            await automod.send(embed=embed)
        
    @commands.command()
    @has_perms(4)
    async def disable(self, ctx, name : str = None):
        """Disables a command or cog. Once a command or cog is disabled only admins can use it with the special n@ or N@
        prefix. To re-enable a command or cog call the `enable` command on it. Disabling cogs works as a sort of "select all" 
        button which means that all commands will be disabled and individual commands can then be enabled separatly for
        fine tuning.


        {usage}

        __Examples__
        `{pre}disable` - print the list of disabled cogs and commands
        `{pre}disable cat` - disables the cat command, after that the cat command only be used by admins using `n@cat`
        `{pre}disable Animals` - disables every command in the the Animals cog"""
        if name is None:
            string = ", ".join([f"**{x}**" for x in self.bot.guild_data[ctx.guild.id]['disabled']])
            return await ctx.send(f"Cogs and Commands disabled on the server: {string}")

        disabled = self.bot.guild_data[ctx.guild.id]["disabled"]
        command = self.bot.get_command(name)
        cog = self.bot.get_cog(name)
        
        if command:
            if command in disabled:
                raise BotError("This command is already disabled.")
                
            await self.bot.db.insert_disabled(ctx.guild.id, name)
            return await ctx.send(f":white_check_mark: | Command **{name}** is now disabled")
            
        if cog:
            disabled_commands = [x.name for x in cog.get_commands() if x.name not in self.bot.guild_data[ctx.guild.id]["disabled"]]
            await self.bot.db.insert_disabled(ctx.guild.id, *disabled_commands)
            return await ctx.send(f":white_check_mark: | All commands in **{name}** are now disabled")  
            
        raise BotError("No such command/cog")

    @commands.command()
    @has_perms(4)
    async def enable(self, ctx, name : str = None):
        """Enable a command or cog. Once a command or cog is enabled everybody can use it given no other restrictions such 
        as blacklisted or ignored. To disable a command or cog call the `disable` comannd on it. Enabling cogs works as a 
        sort of "select all" button which means that all commands will be enabled and individual commands can then be disabled
        separatly for fine tuning.


        {usage}

        __Examples__
        `{pre}enable` - print the list of disabled cogs and commands
        `{pre}enabled cat` - enable the cat command, after that everybody can use it again freely.
        `{pre}enable Animals` - enables every command in the the Animals cog"""
        if not name:
            string = ", ".join([f"**{x}**" for x in self.bot.guild_data[ctx.guild.id]['disabled']])
            return await ctx.send(f"Cogs and Commands disabled on the server: {string}")

        disabled = self.bot.guild_data[ctx.guild.id]["disabled"]
        command = self.bot.get_command(name)
        cog = self.bot.get_cog(name)
        
        if command:
            if command not in disabled:
                raise BotError("This command is not disabled.")
                
            await self.bot.db.delete_disabled(ctx.guild.id, name)
            return await ctx.send(f":white_check_mark: | Command **{name}** is now enabled")
                
            
        if cog:
            enabled_commands = [x.name for x in cog.get_commands() if x.name in self.bot.guild_data[ctx.guild.id]["disabled"]]
            await self.bot.db.delete_disabled(ctx.guild.id, *enabled_commands)
            return await ctx.send(f":white_check_mark: | All commands in **{name}** are now enabled")  
            
        raise BotError("No such command/cog")
     
    #######################################################################
    ## Events
    ####################################################################### 
       
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        role = discord.utils.get(member.roles, id=self.bot.guild_data[member.guild.id]["mute"])
        if role is None:
            return
            
        self.bot.guild_data[member.guild.id]["mutes"].append(member.id)
        automod = self.bot.guild_data[member.guild.id]["automod"]
        if automod:
            embed = discord.Embed(
                title="Mute Evasion", 
                description=f"User **{member}** has left the server while muted.", 
                colour=self.bot.bot_color
            )
            embed.set_footer(**self.bot.bot_footer)
            
            await member.guild.get_channel(automod).send(embed=embed)
            
    @commands.Cog.listener()
    async def on_member_join(self, member):
        role = discord.utils.get(member.guild.roles, id=self.bot.guild_data[member.guild.id]["mute"])
        if role is None:
            return
            
        if member.id in self.bot.guild_data[member.guild.id]["mutes"]:
            await member.add_roles(role)
            self.bot.guild_data[member.guild.id]["mutes"].remove(member.id)
            
            automod = self.bot.guild_data[member.guild.id]["automod"]
            if automod:
                embed = discord.Embed(
                    title="Mute Evasion Countered", 
                    description=f"User **{member}** has rejoined the server and has resumed their mute.", 
                    colour=self.bot.bot_color
                )
                embed.set_footer(**self.bot.bot_footer)
                
                await member.guild.get_channel(automod).send(embed=embed)

def setup(bot):
    bot.add_cog(Moderation(bot))
