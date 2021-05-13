#!/usr/bin/python3.6
import discord
from discord.ext import commands

from rings.utils.utils import has_goodbye, has_welcome, has_automod, BotError
from rings.db import DatabaseError
from rings.misc import FightError

import asyncio
import traceback
import logging

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    #######################################################################
    ## Functions
    #######################################################################
        
    async def dm_reaction_handler(self, payload):
        if payload.emoji.name == "\N{WASTEBASKET}":
            try:
                await self.bot._connection.http.delete_message(payload.channel_id, payload.message_id)
            except (discord.Forbidden, discord.HTTPException):
                pass
                
    async def poll_reaction_handler(self, payload):
        if payload.user_id == self.bot.user.id:
            return 
            
        if str(payload.emoji) not in self.bot.polls[payload.message_id]["list"] and self.bot.polls[payload.message_id]["list"]:
            if await self.bot.db.get_permission(payload.user_id, payload.guild_id) < 4:
                emoji = payload.emoji._as_reaction()
                await self.bot._connection.http.remove_reaction(
                    payload.channel_id,
                    payload.message_id,  
                    emoji, 
                    payload.user_id
                )
                
            return
            
        counter = self.bot.polls[payload.message_id]["voters"].count(payload.user_id) + 1
        if counter > self.bot.polls[payload.message_id]["votes"]:
            if await self.bot.db.get_permission(payload.user_id, payload.guild_id) < 4:
                emoji = payload.emoji._as_reaction()
                await self.bot._connection.http.remove_reaction(
                    payload.channel_id,
                    payload.message_id,  
                    emoji, 
                    payload.user_id
                )
                
                if self.bot.guild_data[payload.guild_id]["automod"]:
                    channel = self.bot.get_channel(self.bot.guild_data[payload.guild_id]["automod"])
                    user = self.bot.get_user(payload.user_id)
                    
                    await channel.send(f":warning:| User {user.mention} tried adding more reactions than allowed to a poll")
            return
            
        await self.bot.db.query_executer(
            "INSERT INTO necrobot.Votes VALUES($1, $2, $3)", 
            payload.message_id, payload.user_id, payload.emoji.name
        )
        self.bot.polls[payload.message_id]["voters"].append(payload.user_id)
        
    async def starred_reaction_handler(self, payload):
        await self.bot.db.update_stars(payload.message_id, payload.user_id, 1)

        if not self.is_starrable(payload.guild_id, payload.channel_id, payload.message_id):
            return

        channel = self.bot.get_channel(payload.channel_id)
        starboard = self.bot.get_channel(self.bot.guild_data[payload.guild_id]["starboard-channel"])
        if channel.is_nsfw() and not starboard.is_nsfw():
            await channel.send(":negative_squared_cross_mark: | Could not send message to starboard because channel is marked as NSFW and starboard id marked as SFW. Either make this channel SFW or make the starboard NSFW")
            return
        
        if not payload.message_id in self.bot.potential_stars:
            message = self.bot._connection._get_message(payload.message_id)
            if message is not None:
                self.bot.potential_stars[payload.message_id] = {"message": message, "count": 0}
            else:
                return
        
        message = self.bot.potential_stars[payload.message_id]
        if not message["message"].author.id == payload.user_id:
            message["count"] += 1
            
        if message["count"] >= self.bot.guild_data[payload.guild_id]["starboard-limit"]:
            del self.bot.potential_stars[payload.message_id]
            await self.bot.meta.star_message(message["message"])
        
    def is_starrable(self, guild_id, channel_id, message_id):
        if self.bot.guild_data[guild_id]["starboard-channel"] in [0, channel_id]:
            return False
            
        if channel_id in self.bot.guild_data[guild_id]["ignore-automod"]:
            return False
            
        if message_id in self.bot.starred:
            return False
            
        return True    
    
    #######################################################################
    ## Events
    #######################################################################
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Catches error and sends a message to the user that caused the error with a helpful message."""
        msg = None     
        error = getattr(error, "original", error)

        if isinstance(error, commands.MissingRequiredArgument):
            msg = f"Missing required argument: `{error.param.name}`! Check help guide with `n!help {ctx.command.qualified_name}`"
        elif isinstance(error, (commands.CheckFailure, commands.BadUnionArgument, commands.BadArgument, BotError)):
            msg = error
        elif isinstance(error, commands.CommandOnCooldown):
            hours, remainder = divmod(error.retry_after, 3600)
            minutes, seconds = divmod(remainder, 60)
            msg = f"This command is on cooldown, retry after **{int(hours)} hours, {int(minutes)} minutes and {int(seconds)} seconds**"
        elif isinstance(error, commands.NoPrivateMessage):
            msg = "This command cannot be used in private messages."
        elif isinstance(error, commands.DisabledCommand):
            msg = f"This command is disabled and cannot be used for now."
        elif isinstance(error, asyncio.TimeoutError):
            if hasattr(error, "timer"):
                minutes, seconds = divmod(error.timer, 60)
                msg = f"You took too long to reply, please reply within **{int(minutes)} minutes and {int(seconds)} seconds** next time"
        elif isinstance(error, commands.BotMissingPermissions):
            msg = f"I need {', '.join(error.missing_perms)} to be able to run this command"
        elif isinstance(error, (DatabaseError, FightError)):
            msg = str(error)
            await self.bot.get_error_channel().send(embed=error.embed(self.bot))
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, discord.Forbidden):
            msg = "Looks like I don't have permission to do this."
        elif isinstance(error, discord.HTTPException) and getattr(error, "status", 0) >= 500:
            msg = "An error occured with Discord's servers. Unable to complete action, the Discord servers might be struggling, please try again later"
        else:
            error_traceback = " ".join(traceback.format_exception(type(error), error, error.__traceback__, chain=True))
            if ctx.guild is not None:
                guild = f"{ctx.guild.name} ({ctx.guild.id})"
                channel = f"{ctx.channel.name} ({ctx.channel.id})"
            else:
                guild = "DM"
                channel = "DM"

            embed = discord.Embed(title="Command Error", description=f"```py\n{error_traceback[:2048]}\n```", colour=discord.Colour(0x277b0))
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
            embed.add_field(name="Command", value=ctx.command.name)
            embed.add_field(name="Author", value=ctx.author.mention)
            embed.add_field(name="Location", value=f"**Guild:** {guild}\n**Channel:** {channel}")
            embed.add_field(name="Message", value=ctx.message.content[:1024], inline=False)
            
            try:
                await self.bot.get_error_channel().send(embed=embed)
            except discord.HTTPException:
                logging.error(error_traceback)

            thing = ctx.guild or ctx.author
            if thing.id != 311630847969198082:
                msg = f"There was an unexpected error. A report has been sent and a fix will be patched through. The error is `{error}`"
        
        if msg is not None: 
            try:     
                await ctx.send(f":negative_squared_cross_mark: | {msg}", delete_after=60)
            except discord.Forbidden:
                pass
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if self.bot.blacklist_check(guild.id):
            return await guild.leave()

        await self.bot.meta.new_guild(guild.id)
        await self.bot.db.update_invites(guild)

        for member in guild.members:
            await self.bot.meta.new_member(member, guild)
            
        await guild.owner.send(embed=self.bot.tutorial_e)
        
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.meta.delete_guild(guild.id)
        
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild_id = channel.guild.id
        guild = self.bot.guild_data[guild_id]

        if channel.id == guild["broadcast-channel"]:
            await self.bot.db.update_broadcast_channel(guild_id)
            
        if channel.id == guild["starboard-channel"]:
            await self.bot.db.update_starboard_channel(guild_id)
            
        if channel.id == guild["welcome-channel"]:
            await self.bot.db.update_greeting_channel(guild_id)
            
        if channel.id == guild["automod"]:
            await self.bot.db.update_automod_channel(guild_id)
        
        await self.bot.db.delete_automod_ignore(guild_id, channel.id)
        await self.bot.db.delete_command_ignore(guild_id, channel.id)
        await self.bot.db.delete_rss_channel(guild_id, channel_id=channel.id)
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild_id = role.guild.id
        guild = self.bot.guild_data[guild_id]

        if role.id == guild["mute"]:
            await self.bot.db.update_mute_role(guild_id)
            
        if role.id in guild["self-roles"]:
            await self.bot.db.delete_self_roles(role.id)
            
        if role.id == guild["auto-role"]:
            await self.bot.db.update_auto_role(role.id)
            
        if role.id in guild["ignore-automod"]:
            await self.bot.db.delete_automod_ignore(guild_id, role.id)
            
        if role.id in guild["ignore-command"]:
            await self.bot.db.delete_command_ignore(guild_id, role.id)
            
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.owner.id != after.owner.id:
            after_perms = 4 if after.get_member(before.owner.id).guild_permissions.administrator else 0
            await self.bot.db.update_permission(before.owner.id, before.id, update=after_perms)
            await self.bot.db.update_permission(after.owner.id, after.id, update=5)
    
    @commands.Cog.listener()     
    async def on_command(self, ctx):
        try:
            can_run = await ctx.command.can_run(ctx) and ctx.command.enabled
        except commands.CheckFailure:
            can_run = False

        guildname = "DM"
        guildid = None
        if ctx.guild:
            guildname = ctx.guild.name
            guildid = ctx.guild.id

        await self.bot.db.query_executer(
            """INSERT INTO necrobot.Logs (user_id, username, command, guild_id, guildname, message, can_run) 
            VALUES($1,$2,$3,$4,$5,$6,$7);""", 
            ctx.author.id, ctx.author.name, ctx.command.name, guildid, guildname, ctx.message.content, can_run
        )
        
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        await self.bot.db.insert_invite(invite)
        
    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        await self.bot.db.delete_invite(invite)
        
    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        pass
        
    @commands.Cog.listener()
    async def on_message_delete(self, message):            
        if message.guild is None or message.author.bot:
            return

        if has_automod(self.bot, message):
            if not message.content:
                message.content = "\U0000200b"

            embed = discord.Embed(title="Message Deleted", description=message.content, colour=discord.Colour(0x277b0))
            embed.set_author(name=message.author, icon_url=message.author.avatar_url)
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
            embed.add_field(name="Info", value=f"In {message.channel.mention} by {message.author.mention}")
            embed.add_field(name="Attachment?", value="Yes" if message.attachments else "No", inline=False)
            channel = self.bot.get_channel(self.bot.guild_data[message.guild.id]["automod"])
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass
            
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):        
        if before.guild is None or before.author.bot or before.content == after.content:
            return

        if has_automod(self.bot, after):
            embed = discord.Embed(title="Message Edited", description=f"In {before.channel.mention} by {before.author.mention}", colour=discord.Colour(0x277b0))
            if not after.content:
                after.content = "\U0000200b"
                
            if not before.content:
                before.content = "\U0000200b"

            embed.set_author(name=before.author, icon_url= before.author.avatar_url)
            embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
            embed.add_field(name="Before", value=before.content if len(before.content) < 1024 else before.content[1020:] + "...", inline=False)
            embed.add_field(name="After", value=after.content if len(after.content) < 1024 else after.content[1020:] + "...", inline=False)
            channel = self.bot.get_channel(self.bot.guild_data[before.guild.id]["automod"])
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass
            
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.bot.db.delete_permission(member.id, member.guild.id)
        await self.bot.db.delete_automod_ignore(member.guild.id, member.id)
        
        await self.bot.meta.new_member(member, member.guild)
        
        if member.bot:
            return
            
        if has_welcome(self.bot, member):
            channel = self.bot.get_channel(self.bot.guild_data[member.guild.id]["welcome-channel"])
            message = self.bot.guild_data[member.guild.id]["welcome"]
            if self.bot.blacklist_check(member.id):
                await channel.send(f":eight_pointed_black_star: | {member.mention}. **You are not welcome here, disturber of the peace**")
            else:
                message = message.format(
                    member=member, 
                    server=member.guild.name,
                    mention=member.mention,
                    name=member.name,
                    id=member.id
                )
                try:
                    await channel.send(message, allowed_mentions=discord.AllowedMentions())
                except discord.Forbidden:
                    pass
                
        invite = await self.bot.db.update_invites(member.guild)
        
        if self.bot.guild_data[member.guild.id]["automod"]:
            channel = member.guild.get_channel(self.bot.guild_data[member.guild.id]["automod"])
            if invite:
                embed = discord.Embed(title="Member Joined", description=f"{member.mention} has joined the server using {invite.url}", colour=discord.Colour(0x277b0))
                embed.add_field(name="Invite", value=invite.inviter)
                embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))
                
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass
                    
            else:
                embed = discord.Embed(title="Member Joined", description=f"{member.mention} has joined the server but didn't use an invite... somehow...", colour=discord.Colour(0x277b0))
                embed.set_footer(text="Generated by Necrobot", icon_url=self.bot.user.avatar_url_as(format="png", size=128))

                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass
                
        if self.bot.guild_data[member.guild.id]["auto-role"]:
            role = discord.utils.get(member.guild.roles, id=self.bot.guild_data[member.guild.id]["auto-role"])
            await member.add_roles(role)

            if self.bot.guild_data[member.guild.id]["auto-role-timer"] > 0:
                await asyncio.sleep(self.bot.guild_data[member.guild.id]["auto-role-timer"])
                try:
                    await member.remove_roles(role)
                except discord.HTTPException:
                    pass
                    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self.bot.db.delete_permission(member.id, member.guild.id)
        await self.bot.db.delete_automod_ignore(member.guild.id, member.id)

        if has_goodbye(self.bot, member):
            channel = self.bot.get_channel(self.bot.guild_data[member.guild.id]["welcome-channel"])
            message = self.bot.guild_data[member.guild.id]["goodbye"]

            if member.id in self.bot.settings["blacklist"]:
                await channel.send(":eight_pointed_black_star: | **...**")
            else:
                message = message.format(
                    member=member, 
                    server=member.guild.name,
                    mention=member.mention,
                    name=member.name,
                    id=member.id
                )
                try:
                    await channel.send(message, allowed_mentions=discord.AllowedMentions())
                except discord.Forbidden:
                    pass
                
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if self.bot.blacklist_check(payload.user_id):
            return

        if payload.guild_id is None:
            return await self.dm_reaction_handler(payload)
            
        if payload.message_id in self.bot.polls:
            return await self.poll_reaction_handler(payload)

        if payload.emoji.name == "\N{WHITE MEDIUM STAR}":
            return await self.starred_reaction_handler(payload)
                    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.user_id in self.bot.settings["blacklist"] or payload.guild_id is None:
            return
            
        if payload.message_id in self.bot.polls:
            if payload.user_id == self.bot.user.id:
                return
                
            result = await self.bot.db.query_executer(
                "DELETE FROM necrobot.Votes WHERE message_id = $1 AND user_id = $2 AND reaction = $3 RETURNING user_id", 
                payload.message_id, payload.user_id, payload.emoji.name
                ) 
            
            if result:
                self.bot.polls[payload.message_id]["voters"].remove(payload.user_id)
            
        if payload.emoji.name == "\N{WHITE MEDIUM STAR}":
            if payload.message_id in self.bot.potential_stars:
                message = self.bot.potential_stars[payload.message_id]
                
                if not message["message"].author.id == payload.user_id:
                    message["count"] -= 1

            await self.bot.db.update_stars(payload.message_id, payload.user_id, -1)
    
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.message_id in self.bot.potential_stars:
            message = self.bot.potential_stars[payload.message_id]["message"]
            message._update(payload.data)
            
    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        if payload.message_id in self.bot.potential_stars:
            self.bot.potential_stars[payload.message_id]["count"] = 0  
        
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if payload.message_id in self.bot.potential_stars:
            del self.bot.potential_stars[payload.message_id]

def setup(bot):
    bot.add_cog(Events(bot))
